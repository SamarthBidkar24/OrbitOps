import json
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.db.models import User, ChatSession
class SQLiteManager:
    def __init__(self, session_class):
        self.SessionLocal = session_class

    def get_session(self):
        return self.SessionLocal()

    def get_user_by_email(self, email: str) -> User | None:
        with self.get_session() as session:
            return session.scalar(select(User).where(User.email == email))

    def get_user_by_username(self, username: str) -> User | None:
        with self.get_session() as session:
            return session.scalar(select(User).where(User.username == username))

    def create_user_with_hash(self, email: str, username: str, hashed_password: str) -> User:
        """Create user with an already computed hash."""
        user = User(email=email, username=username, hashed_password=hashed_password)
        with self.get_session() as session:
            session.add(user)
            session.commit()
            session.refresh(user)
        return user

    def create_user(self, email: str, username: str, password: str) -> User:
        """Helper for simple creation (for testing/compatibility), hashing internally."""
        from passlib.context import CryptContext
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        hashed = pwd_context.hash(password)
        return self.create_user_with_hash(email, username, hashed)

    def create_chat_session(self, user_id: int, title: str = "New Chat") -> ChatSession:
        session = ChatSession(user_id=user_id, title=title, messages="[]")
        with self.get_session() as db:
            db.add(session)
            db.commit()
            db.refresh(session)
        return session

    def get_chat_sessions(self, user_id: int) -> list[ChatSession]:
        with self.get_session() as db:
            return db.scalars(
                select(ChatSession).where(ChatSession.user_id == user_id).order_by(ChatSession.updated_at.desc())
            ).all()

    def get_chat_session(self, session_id: int) -> ChatSession | None:
        with self.get_session() as db:
            return db.get(ChatSession, session_id)

    def add_message(self, session_id: int, role: str, content: str):
        with self.get_session() as db:
            session = db.get(ChatSession, session_id)
            if not session:
                return
            msgs = json.loads(session.messages) if session.messages else []
            msgs.append({"role": role, "content": content, "timestamp": datetime.utcnow().isoformat()})
            session.messages = json.dumps(msgs)
            session.updated_at = datetime.utcnow()
            db.commit()

    def get_messages(self, session_id: int) -> list[dict]:
        with self.get_session() as db:
            session = db.get(ChatSession, session_id)
            if not session:
                return []
            return json.loads(session.messages) if session.messages else []
