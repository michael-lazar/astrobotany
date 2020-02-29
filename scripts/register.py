#!/usr/local/bin/python3.7
"""
This is a cgi script that takes an PKCS#10 certificate signing request (csr)
and returns a signed client certificate.
"""
import cgi
import os
import secrets
import subprocess
import sys

CA = "/etc/pki/tls/jetforce_client/ca.cer"
CAKEY = "/etc/pki/tls/jetforce_client/ca.key"

html = """\
<!DOCTYPE html>
<html>
<body>
<div>
<form method="post" enctype="multipart/form-data">
    Upload your PKCS#10 Certificate Signing Request<br/>
    <input type="file" name="req""><br/>
    <input type="submit" value="Submit" name="submit">
</form>
</div>
</body>
</html>
"""

if os.environ["REQUEST_METHOD"] != "POST":
    print("Status: 200 Success")
    print("Content-Type: text/html")
    print("")
    print(html)
    sys.exit()


form = cgi.FieldStorage()
if "req" not in form:
    print("Status: 400 Bad Request")
    sys.exit()


request = form["req"].value
serial = "0x" + secrets.token_hex(16)
command = [
    "openssl",
    "x509",
    "-req",
    "-CA",
    CA,
    "-CAkey",
    CAKEY,
    "-set_serial",
    serial,
    "-extensions",
    "client",
    "-days",
    "3650",
    "-outform",
    "PEM",
]

proc = subprocess.run(command, input=request, capture_output=True)
proc.check_returncode()

print("Status: 200 Success")
print("Content-Type: application/x-x509-ca-cert")
print("", flush=True)

# Return the client certificate
sys.stdout.buffer.write(proc.stdout)
