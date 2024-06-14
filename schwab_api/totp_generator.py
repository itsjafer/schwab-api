import base64
from vipaccess import provision as vp


def generate_totp():
    """ Generates an authentication pair of Symantec VIP ID, and TOTP Secret

    :rtype: (str, str)
    """
    request = vp.generate_request()
    session = vp.requests.Session()
    response = vp.get_provisioning_response(request, session)
    otp_token = vp.get_token_from_response(response.content)
    otp_secret = vp.decrypt_key(otp_token['iv'], otp_token['cipher'])
    otp_secret_b32 = base64.b32encode(otp_secret).upper().decode('ascii')

    return otp_token['id'], otp_secret_b32
