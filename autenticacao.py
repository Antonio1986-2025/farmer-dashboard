"""Autenticação JWT para o AgroSinal."""
from datetime import datetime, timedelta, timezone
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from config import JWT_SECRET, JWT_ALGORITHM, JWT_EXPIRACAO_DIAS
from dados import banco

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
seguranca = HTTPBearer(auto_error=False)


def hash_senha(senha: str) -> str:
    return pwd_context.hash(senha)


def verificar_senha(senha: str, hash_: str) -> bool:
    return pwd_context.verify(senha, hash_)


def criar_token(usuario_id: int) -> str:
    exp = datetime.now(timezone.utc) + timedelta(days=JWT_EXPIRACAO_DIAS)
    return jwt.encode({"sub": str(usuario_id), "exp": exp}, JWT_SECRET, algorithm=JWT_ALGORITHM)


def _decodificar(token: str):
    payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    usuario_id = int(payload.get("sub"))
    usuario = banco.pegar_usuario_por_id(usuario_id)
    if not usuario:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuário não encontrado")
    return usuario


async def pegar_usuario_atual(
    request: Request,
    creds: HTTPAuthorizationCredentials | None = Depends(seguranca),
):
    """Verifica token no header Authorization ou no cookie 'token'."""
    token = None
    if creds is not None:
        token = creds.credentials
    if not token:
        token = request.cookies.get("token")
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Faça login primeiro")
    try:
        return _decodificar(token)
    except (JWTError, ValueError, TypeError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")
