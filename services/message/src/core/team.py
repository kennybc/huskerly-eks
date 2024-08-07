
from core.organization import check_assist_admin_perm, check_in_org
from utils.connect import get_cursor


def check_in_team(user_email: str, team_id: int) -> bool:
    with get_cursor() as cursor:
        cursor.execute(
            """
            SELECT user_email
            FROM team_users
            WHERE user_email = %s AND team_id = %s
            """, (user_email, team_id))

        return cursor.fetchone() is not None


def check_team_perm(current_user_email: str, team_id: int) -> bool:
    with get_cursor() as cursor:
        cursor.execute(
            """
                SELECT o.org_id
                FROM teams t
                JOIN organizations o ON t.org_id = o.id
                WHERE t.id = %s
                """, (team_id,))

        org_id = cursor.fetchone()[0]

        return not (check_in_team(current_user_email, team_id) or check_assist_admin_perm(current_user_email, org_id))


def get_team(team_id: int) -> dict:
    with get_cursor() as cursor:
        cursor.execute(
            """
            SELECT t.name AS team_name, tu.user_email
            FROM teams t
            JOIN team_users tu ON t.id = tu.team_id
            WHERE t.id = %s AND t.deleted = FALSE
            """, (team_id,))

        result = cursor.fetchall()
        team_info = {"team_name": result[0][0],
                     "users": [row[1] for row in result]}
        return team_info


def create_team(team_name: str, creator_email: str, org_id: int) -> int:
    with get_cursor() as cursor:
        team_id = None

        cursor.execute(
            """
            INSERT INTO teams (name, created_by_email, organization_id)
            VALUES (%s, %s, %s)
            """, (team_name, creator_email, org_id))

        if cursor.rowcount == 1:
            cursor.execute("SELECT LAST_INSERT_ID()")
            team_id = cursor.fetchone()[0]
            join_team(team_id, creator_email)

        return team_id


def join_team(team_id: int, user_email: str) -> bool:
    with get_cursor() as cursor:

        # Check if the team exists and is not deleted
        cursor.execute(
            """
            SELECT deleted, org_id
            FROM teams
            WHERE id = %s
            """, (team_id,))

        result = cursor.fetchone()
        if result is None or result[0]:
            return False

        org_id = result[1]

        # Check if the user is in the organization
        if not check_in_org(user_email, org_id):
            raise Exception("User is not in this organization")

        cursor.execute(
            """
            INSERT INTO team_members (team_id, user_email)
            VALUES (%s, %s)
            """, (team_id, user_email))

        return cursor.rowcount == 1


def leave_team(team_id: int, current_user_email: str, user_email: str) -> bool:
    with get_cursor() as cursor:

        if not check_team_perm(current_user_email, team_id):
            raise Exception(
                "User does not have permission to perform this action")

        cursor.execute(
            """
            DELETE FROM team_users
            WHERE team_id = %s AND user_email = %s
            """, (team_id, user_email))

        return cursor.rowcount == 1


def edit_team(team_id: int, current_user_email: str, team_name: str) -> bool:
    with get_cursor() as cursor:

        if not check_team_perm(current_user_email, team_id):
            raise Exception(
                "User does not have permission to perform this action")

        cursor.execute(
            """
            UPDATE teams
            SET name = %s
            WHERE id = %s AND deleted = FALSE
            """, (team_name, team_id))

        return cursor.rowcount == 1


def delete_team(current_user_email: str, team_id: int) -> bool:
    with get_cursor() as cursor:

        if not check_team_perm(current_user_email, team_id):
            raise Exception(
                "User does not have permission to perform this action")

        cursor.execute(
            """
            UPDATE teams
            SET deleted = TRUE
            WHERE id = %s
            """, (team_id,))
        return cursor.rowcount == 1
