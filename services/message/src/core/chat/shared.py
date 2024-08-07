from core.organization import check_assist_admin_perm
from utils.error import UserError, ServerError
from utils.connect import get_cursor

def check_chat_view_perm(current_user_email: str, chat_id: int) -> bool:
    with get_cursor() as cursor:
        cursor.execute(
            """
                SELECT o.org_id, c.public
                FROM chats c
                JOIN teams t ON c.team_id = t.id
                JOIN organizations o ON t.organization_id = o.org_id
                WHERE c.id = %s
                """, (chat_id,))

        org_id, public = cursor.fetchone()

        return public or check_in_chat(current_user_email, chat_id) or check_assist_admin_perm(current_user_email, org_id)

def check_chat_edit_perm(current_user_email: str, chat_id: int) -> bool:
    with get_cursor() as cursor:
        cursor.execute(
            """
                SELECT o.org_id, c.public
                FROM chats c
                JOIN teams t ON c.team_id = t.id
                JOIN organizations o ON t.organization_id = o.org_id
                WHERE c.id = %s
                """, (chat_id,))

        org_id = cursor.fetchone()[0]

        return check_in_chat(current_user_email, chat_id) or check_assist_admin_perm(current_user_email, org_id)
    
def check_chat_exists_and_not_deleted(chat_id: int) -> bool:
    with get_cursor() as cursor:
        cursor.execute(
            """
            SELECT deleted
            FROM chats
            WHERE id = %s
            """, (chat_id,))

        result = cursor.fetchone()
        return result is not None and not result[0]
    
def check_in_chat(user_email: str, chat_id: int) -> bool:
    with get_cursor() as cursor:
        cursor.execute(
            """
            SELECT user_email
            FROM chat_users
            WHERE user_email = %s AND chat_id = %s
            """, (user_email, chat_id))

        return cursor.fetchone() is not None


def get_posts(current_user_email: str, chat_id: int) -> dict:
    with get_cursor() as cursor:
        if not check_chat_exists_and_not_deleted(chat_id):
            raise UserError("Chat does not exist or has been deleted")
        
        if not check_chat_view_perm(current_user_email, chat_id):
            raise UserError("User does not have permission to view this chat")
        
        cursor.execute(
            """
            SELECT p.id, p.content, p.created_at, p.edited_at, p.user_email
            FROM posts p
            JOIN chats c ON p.chat_id = c.id
            WHERE p.chat_id = %s AND c.deleted = FALSE
            """, (chat_id,))

        result = cursor.fetchall()
        post_history = [{"id": row[0],
                         "content": row[1],
                         "created_at": row[2],
                         "edited_at": row[3],
                         "user_email": row[4]} for row in result]
        return post_history


def join_chat(chat_id: int, user_email: str, override_visibility_perm: bool = False):
    with get_cursor() as cursor:
        if not check_chat_exists_and_not_deleted(chat_id):
            raise UserError("Chat does not exist or has been deleted")
        
        if not override_visibility_perm and not check_chat_view_perm(user_email, chat_id):
            raise UserError("User does not have permission to view this chat")
        
        if check_in_chat(user_email, chat_id):
            raise UserError("User is already in this chat")

        cursor.execute(
            """
            INSERT INTO chat_users (chat_id, user_email)
            VALUES (%s, %s)
            """, (chat_id, user_email))

        if not cursor.rowcount == 1:
            raise ServerError("Failed to join chat")


def delete_chat(current_user_email: str, chat_id: int) -> bool:
    with get_cursor() as cursor:
        if not check_chat_exists_and_not_deleted(chat_id):
            raise UserError("Chat does not exist or is already deleted")
        
        if not check_chat_edit_perm(current_user_email, chat_id):
            raise UserError("User does not have permission to delete this chat")
        
        cursor.execute(
            """
            UPDATE chats
            SET deleted = TRUE
            WHERE id = %s
            """, (chat_id,))
        
        if not cursor.rowcount == 1:
            raise ServerError("Failed to delete chat")
