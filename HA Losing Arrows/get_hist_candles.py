#34.127.53.74
import moomoo as ft
from moomoo import RET_OK, SysConfig
from time import sleep
import os

content = """
-----BEGIN RSA PRIVATE KEY-----
MIICWwIBAAKBgQCqPhQIQ5hUIUagZCE6BmUNtKzAXzwNqsehm2+RK+tf0LBtOyFx
NAXSFsvLUZ16G7i6o/RyskAuHANjnk+L+SMn0t6zAJJ3gPvYui1g7HjsvUlTOg6X
8TfYWsEQZtXIEbL5Q4k9t5jXhrjO8WNIXD9PElfVPQxpzs8Ps2GiCuB5BQIDAQAB
AoGAF2wik+9+4AZTAgK8uo/CLARRZ0dDCytVu4OX8jx9bgmXmHOz+m/6pAjMYa0Z
MkFppU4k9fnV0DI8+iIAFkVBA4Jxdi6xZtQJ6bn6iA4wNFelNwFGUK+qhp5XmxK6
FJM1M9TuIs9gx3jMqFFXMbTQLNC9XptHwAt+s4RfmgCmyiECQQDN0Be/2BeJZibS
hDzXVz9umtgUdViW4hjF6D6qaYsEhLghusqesxSX6VT0peFBuUBdPcipU1DbNMo6
WrLNaN8lAkEA08F/loLIk+NLvaXjnsm4Cyv7W0cuwi2mvhYj9K0pWLyv12LIJNc6
redQpi48m7dHGkjAJlHvN09Cqr6Yo3Z8YQJARk3mPvdfGuVVL6ZSbjD0jyC/3UU0
jN4RHlG2TlodTd7UU1lOa6W6zCW9ipC7gMr6TJ+VUxoNzcObrRFccMR5LQJAPL3B
inwDayCFBmaCb3bvewznshwuFncf4GDbeYD+Xjzpt7/XJ3Ixm9bBdJnIuuYM2EZM
D/Hqy5PJzM6VXDZNoQJAaBqhiBvhnE0Huv2xkS4UOWLTKMq/85ePDfxA7EEVSHZr
a+BxjnNjbFmbxwFGJnB4QS5/7xfVhjSyJK4bjc5Llw==
-----END RSA PRIVATE KEY-----
"""

SysConfig.enable_proto_encrypt(True)
rsa_path = "private_rsa_key.pem"

if os.path.exists(file_path) == False:
    # Open a file in write mode (this will create the file if it does not exist)
    with open(rsa_path, 'w') as file:
        # Write the string to the file
        file.write(content)

SysConfig.set_init_rsa_file(rsa_path)   # rsa private key file path

print("Starting tests")
quote_ctx = ft.OpenQuoteContext(host='0.0.0.0', port=11111)
print("Sleep for 5 seconds")
sleep(5)

ret, data, page_req_key = quote_ctx.request_history_kline('HK.00700', start='2019-09-11', end='2019-09-18', max_count=5) # 5 per page, request the first page
if ret == RET_OK:
    print(data)
else:
    print(RET_OK)
print("Close quote context")
quote_ctx.close()
