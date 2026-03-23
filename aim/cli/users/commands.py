import click
import bcrypt

from aim.storage.structured.sql_engine.models import AimUser


def _get_session():
    from aim.sdk import Repo
    repo = Repo.default_repo()
    repo.structured_db.run_upgrades()
    return repo.structured_db.get_session()


@click.group()
def users():
    """Manage Aim users."""
    pass


@users.command()
@click.option('--username', required=True, help='Username')
@click.option('--password', prompt=True, hide_input=True, confirmation_prompt=True, help='Password')
@click.option('--admin', is_flag=True, default=False, help='Grant admin privileges')
def create(username, password, admin):
    """Create a new user."""
    session = _get_session()

    existing = session.query(AimUser).filter(AimUser.username == username).first()
    if existing:
        click.echo(f'Error: User "{username}" already exists.')
        raise SystemExit(1)

    pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    user = AimUser(username=username, password_hash=pw_hash, is_admin=admin)
    session.add(user)
    session.commit()

    role = 'admin' if admin else 'user'
    click.echo(f'Created {role}: {username}')


@users.command('list')
def list_users():
    """List all users."""
    session = _get_session()
    all_users = session.query(AimUser).all()

    if not all_users:
        click.echo('No users found.')
        return

    click.echo(f'{"ID":<6} {"Username":<20} {"Admin":<8} {"Created At"}')
    click.echo('-' * 60)
    for u in all_users:
        click.echo(f'{u.id:<6} {u.username:<20} {str(u.is_admin):<8} {u.created_at}')


@users.command('reset-password')
@click.option('--username', required=True, help='Username')
@click.option('--password', prompt=True, hide_input=True, confirmation_prompt=True, help='New password')
def reset_password(username, password):
    """Reset a user's password."""
    session = _get_session()
    user = session.query(AimUser).filter(AimUser.username == username).first()
    if not user:
        click.echo(f'Error: User "{username}" not found.')
        raise SystemExit(1)

    user.password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    session.commit()
    click.echo(f'Password reset for user: {username}')
