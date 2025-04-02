from typing import Dict, Any
from pydantic import BaseModel

class GlobalVars(BaseModel):
    jsrsasign_js: str = """  """
    llavepem: str = """-----BEGIN PRIVATE KEY-----
MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQCy6AilxKvf90rO
TiahSW5r6rqAX+HmwX3c1EKeHQ5U5DNsIP+ytXnCoi9rqCNmGPULboBrF39Kv+ND
060gxvUVD+cG0vd+eMZ7cF8Uag3JEg7zQ4oJCS0TJveFKZ8kx/RkUSxUHnU8VqCb
jnurJ45bXuaUY+MKt57w4nIAjZHt6cp4WUOrjooUVVtbLTKo0MhVos7FfyA/HPh2
cvDII1nmFRj1L+Y4yWM6VjBivMo1MSSI956LuvLwtholQV9Jm6t1TWGYMPnD1sdn
bCrIZnOG0/IbTI3535MJoUAWZtl72uZOe9gb2S6g9DNIpkttVGX9enK1X9rmGzpW
fYJd6MJTAgMBAAECggEANEAxWly8x+4dAnDvtlZQciM9cgXO38quHEM/65bX2zJE
1HU0yLhYxeABUoNqR0TNuJd+2QglTKsLUIFvhG2nIY4h7qvJzb2vVljk4/zvZsSn
6iNVGrt71yafztvvl1nwxiWw+SZmHge844GzG7MzT/tBA6DCrBwhxv+TxRaTwrRy
w65zzNGhn1l6kh7kO0uQiT+opNxZnCMTO37pL1A9U0GXBQt1G9a+GNFyU8ga8nee
h16P+AIKY4t6N335WbBPcxbrPsfvurzJH94mqFIBQ4g5VcZ7f6sgB6+jOkFGzRy8
5C8bpkJ29xNc5QflurnRabKkxie9pRXY5+Mw1uQ+1QKBgQDUqbUyCc3OzIbGXqJ8
D0rHQ1LfwY7Z777gzjdJpv1OUnCtSD29BKHI6fWKy60gQjkwdPxCode9mm4Rsn3S
ixMXlGf5XrWhmX3HAPli6W9HhNlNX0UYgh0Z9TdbDE+0QUEXSfYkn3/EhNcflDMp
NHgdLTmwTFj4HRIfnWrfUT+D3wKBgQDXXUzTTvUKhr2aj/xmoR+AitmPxEEvj0h8
uQXshznYQEWOaHelWeZ7Wb1CMT1oxCETAeQpowqLgnXHJyx6H9ik2IMLZOn6/o71
ECFqOJuZr+enMFNG3jjiSc20hGOs2A/EerjO8ijVk12M7briymJYPbfV4UQXb/yD
HCbiH7LwDQKBgE6ePqI1BaTB78E+EwuSC68GsIiP4eOnwgURt1a/KT3fNFCbOFe8
cqL3+xJIocQfN002sltfwYYSpUZdmi5Pw8sfziBeZv9K4zjCn291pPHnpv33jm+1
ClUiVkiOkJiu1wVpDloTrQRVp8HA4/kDsLP4mC8YyntPI/gUFgJg4v45AoGBANVN
1V+c3lp0papGXgkQIHFiFKWuDZobYgIWB2YDcSlcTwgDNC2TYxJdCXRb7KStTMzU
nLUYhMM0jY6YoBa9IAf1YaWRZ6VvJwxV06KvOn33mYsf8/tG8jQ+QP0/+rEgtk01
94EQm50dfhStCOLC7LDVQBUYLibAhesdoO1p1AKpAoGABkNxzrIMeOGEOVeYE/Zg
D7PQyT/sDCrE+9ZWleTA2stPwMNVQPaBciv2mXe6CrIgTJxXNdfNp6LRsVEAD8n5
qSeNw2bXPrcL6lzXZ2ZJ0ny9Z6Xo8/07pAILPBtneaDunE/nFr9U6YDBw1hXpCW1
222pj31oJJFQnRxQNTwqHws=
-----END PRIVATE KEY-----"""
    llavehmaccliente: str = "vQOzjLPEuo/lXJN4AdlQ7hpnVvqHy7iw"
    accessToken: str = "postman.getGlobalVariable"
    usuarioAseguradoraCliente: str = "900133384"

    @classmethod
    def get_all(cls) -> Dict[str, Any]:
        return cls().dict()

    @classmethod
    def get_value(cls, key: str) -> str:
        return cls().dict().get(key, "") 