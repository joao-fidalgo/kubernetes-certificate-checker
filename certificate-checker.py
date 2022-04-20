import requests
import os
import urllib3
urllib3.disable_warnings()
import OpenSSL.crypto
import base64
from datetime import datetime, timedelta
import pymsteams

CLUSTER_NAME = os.getenv("CLUSTER_NAME", "changeme")
DAYS_UNTIL = int(os.getenv("DAYS_UNTIL", 3))
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "changeme")

KUBERNETES_API_URL = os.environ["KUBERNETES_PORT_443_TCP_ADDR"]
with open("/var/run/secrets/kubernetes.io/serviceaccount/token", "r") as file:
  KUBERNETES_API_TOKEN = file.read()

def sendAlert(namespace, secret_name, expiration_date):
  card = pymsteams.connectorcard(WEBHOOK_URL)
  card.summary("Alert")
  
  section = pymsteams.cardsection()
  section.title("Certificate expiring in less than {days_until} days".format(days_until=DAYS_UNTIL))
  section.addFact("Cluster", CLUSTER_NAME)
  section.addFact("Namespace", namespace)
  section.addFact("Secret Name", secret_name)
  section.addFact("Expiration Date", str(expiration_date))

  card.addSection(section)
  card.send()

def get_expiration_date(tls_crt):
  if tls_crt == None:
    return None

  pem = OpenSSL.crypto.load_certificate(
    OpenSSL.crypto.FILETYPE_PEM,
    base64.b64decode(tls_crt)
  )

  expiration_date = datetime.strptime(pem.get_notAfter().decode("UTF-8"), "%Y%m%d%H%M%Sz")
  return expiration_date

def get_tls_crt(secret):
  if secret == None:
    return None

  try:
    tls_crt = secret["data"]["tls.crt"]
    return tls_crt
  except Exception:
    return None

def get_secret(namespace, secret_name):
  if namespace == None or secret_name == None:
    return None

  return requests.get("https://{url}/api/v1/namespaces/{namespace}/secrets/{secret}".format(
      url = KUBERNETES_API_URL,
      namespace = namespace,
      secret = secret_name
    ),
    headers={"Authorization": "Bearer {token}".format(token = KUBERNETES_API_TOKEN)},
    verify=False).json()

def get_certificate_secret_name(certificate):
  try:
    secret_name = certificate["spec"]["secretName"]
    return secret_name
  except Exception:
    return None

def get_certificate_namespace(certificate):
  try:
    namespace = certificate["metadata"]["namespace"]
    return namespace
  except Exception:
    return None

def getCertificates():
  r = requests.get("https://{url}/apis/cert-manager.io/v1/certificates".format(url = KUBERNETES_API_URL),
          headers={"Authorization": "Bearer {token}".format(token = KUBERNETES_API_TOKEN)},
          verify=False).json()

  try:
    certificates = r["items"]
    return certificates
  except Exception:
    return []

def main():
  certificates = getCertificates()

  for i in range(len(certificates)):
    namespace = get_certificate_namespace(certificates[i])
    secret_name = get_certificate_secret_name(certificates[i])
    expiration_date = get_expiration_date(get_tls_crt(get_secret(namespace, secret_name)))
    
    if expiration_date != None and expiration_date < datetime.now() + timedelta(days = DAYS_UNTIL):
      sendAlert(namespace, secret_name, expiration_date)

if __name__ == "__main__":
    main()