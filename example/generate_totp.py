from schwab_api import generate_totp

symantec_id, totp_secret = generate_totp()

print("Your symantec ID is: " + symantec_id)
print("Your TOTP secret is: " + totp_secret)
