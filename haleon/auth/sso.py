import base64, hashlib, secrets, os, httpx, jwt
import logging
from authlib.integrations.requests_client import OAuth2Session
from dotenv import load_dotenv
from datetime import datetime, timezone

load_dotenv()
logger = logging.getLogger("haleon.auth.sso")

class SSO:
    def __init__(
        self,
        client_id: str = None,
        auth_url: str = None,
        token_url: str = None,
        redirect_uri: str = None,
        scopes: str = None,
        verify: bool = None,
        jwks_url: str = None,
        issuer: str = None
    ):
        self.client_id = client_id or os.getenv("CLIENT_ID")
        self.auth_url = auth_url or os.getenv("AUTH_URL")
        self.token_url = token_url or os.getenv("TOKEN_URL")
        self.redirect_uri = redirect_uri or os.getenv("REDIRECT_URI")
        self.scopes = (scopes or os.getenv("SCOPES", "openid profile email")).split()
       
        verify_env = os.getenv("VERIFY", "true").strip().lower()
        if verify_env in ["true", "false"]:
            self.verify = verify_env == "true"
        else:
            self.verify = verify_env  # Chemin vers certificat
           
        self.jwks_url = jwks_url or os.getenv("JWKS_URL")
        self.issuer = issuer or os.getenv("ISSUER")

        # Variables dynamiques
        self.code_challenge_method = "S256"
        self.code_verifier = None
        self.access_token = None
        self.id_token = None
        self.state = None  # Stockage du state
        self.email = None
        self.first_name = None
        self.family_name = None
        self.country = None

        self.session = OAuth2Session(
            client_id=self.client_id,
            redirect_uri=self.redirect_uri,
            scope=self.scopes,
            code_challenge_method=self.code_challenge_method
        )

    @staticmethod
    def _b64url(b: bytes) -> str:
        return base64.urlsafe_b64encode(b).rstrip(b"=").decode()

    def _make_pkce(self) -> tuple[str, str]:
        verifier = self._b64url(secrets.token_bytes(48))
        challenge = self._b64url(hashlib.sha256(verifier.encode()).digest())
        return verifier, challenge

    def get_authorization_url(self):
        try:
            self.code_verifier, challenge = self._make_pkce()
            auth_url, state = self.session.create_authorization_url(
                self.auth_url,
                code_challenge=challenge,
                code_challenge_method=self.code_challenge_method
            )
            self.state = state  # Stockage du state
            return auth_url, state
        except Exception as e:
            logger.exception("SSO get_authorization_url failed: %s", e)
            return None, None

    def validate_state(self, returned_state: str) -> bool:
        return returned_state == self.state

   
    def fetch_tokens(self, code: str):
        try:
            token = self.session.fetch_token(
                self.token_url,
                code=code,
                code_verifier=self.code_verifier,
                verify=self.verify  # ✅ Ajout pour gérer SSL (False ou chemin vers certificat)
            )
            self.access_token = token.get("access_token")
            self.id_token = token.get("id_token")
            return token
        except Exception as e:
            logger.exception("SSO fetch_tokens failed: %s", e)
            return None

    def verify_id_token(self):
        try:
            jwks = httpx.get(self.jwks_url, verify=self.verify).json()
            header = jwt.get_unverified_header(self.id_token)
            kid = header.get("kid")
            key = next((k for k in jwks["keys"] if k["kid"] == kid), None)
            if not key:
                raise ValueError("Clé publique introuvable")
            public_key = jwt.algorithms.RSAAlgorithm.from_jwk(key)
            claims = jwt.decode(
                self.id_token,
                key=public_key,
                algorithms=["RS256"],
                audience=self.client_id,
                issuer=self.issuer
            )

            # ✅ Vérification de l'expiration
            exp = claims.get("exp")
            if exp and datetime.now(timezone.utc).timestamp() > exp:
                raise ValueError("Le token a expiré")

            self.email = claims.get("email")
            self.country = claims.get("country")
            self.first_name = claims.get("given_name")
            self.family_name = claims.get("family_name")
            return claims
        except Exception as e:
            logger.exception("SSO verify_id_token failed: %s", e)
            return None

    def get_userinfo(self):
        try:
            resp = httpx.get(os.getenv("USERINFO_ENDPOINT"), headers={"Authorization": f"Bearer {self.access_token}"})
            return resp.json()
        except Exception as e:
            logger.exception("SSO get_userinfo failed: %s", e)
            return None

    def refresh_token(self, refresh_token: str):
        """Optionnel: gestion du refresh token"""
        try:
            token = self.session.refresh_token(self.token_url, refresh_token=refresh_token)
            self.access_token = token.get("access_token")
            self.id_token = token.get("id_token")
            return token
        except Exception as e:
            logger.exception("SSO refresh_token failed: %s", e)
            return None