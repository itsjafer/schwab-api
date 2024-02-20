import json

def generate_option_symbol(Root, Expiration_YYMMDD, Strike_Price, Type):
    if Type == "Call" or Type == "Put"
        Type = "C" if Type == "Call" else "P"
    else:
          raise ValueError("Type is invalid, it must be 'Call' or 'Put'")
    
    return Root+"  "+Expiration_YYMMDD+Type+Strike_Price
