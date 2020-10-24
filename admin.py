#! /usr/bin/env python

import sys
import string
import os
import random
import itertools

import click
import lorem

from sqlalchemy import create_engine

from gridt.db import Session, Base
from gridt.controllers.helpers import session_scope
from gridt.models import Movement, User, MovementUserAssociation as MUA
from gridt.controllers.user import register
from gridt.controllers.movements import subscribe


@click.group()
@click.option(
    "--uri",
    default=None,
    envvar="ADMIN_DB_URI",
    help="URI of the database, overwrites environment variable ADMIN_DB_URI",
)
@click.pass_context
def cli(ctx, uri):
    ctx.ensure_object(dict)
    ctx.obj["uri"] = uri


@cli.group(short_help="Create new row(s) in the database.")
def create():
    pass


@create.group(
    name="many",
    help="""
         Create many of one type in the database with random
         information.
         """,
)
def create_many():
    pass


@cli.group(help="Count the number of rows of one type")
def count():
    pass


def configure_uri(ctx):
    uri = ctx.obj["uri"]
    if not uri:
        click.secho("No database URI provided, exiting.")
        sys.exit(1)

    engine = create_engine(uri)
    ctx.obj["engine"] = engine
    Session.configure(bind=engine)


def create_random_movement():
    interval = random.choice(["daily", "weekly"])
    movement = Movement(
        lorem.sentence()[:49],
        interval,
        lorem.paragraph()[:100],
        lorem.paragraph()[:1000],
    )
    return movement


@cli.command(short_help="Create the required tables in the database.")
@click.pass_context
def initialize_database(ctx):
    configure_uri(ctx)
    Base.metadata.create_all(ctx.obj["engine"])


@create_many.command(
    name="users",
    short_help="Register many random users in the database.",
    help="""
         Only to be used in testing scenarios, as it assumes to be the only
         one writing new users to the database.
         """,
)
@click.option(
    "--number",
    "-n",
    default=100,
    help="Number of random users to be generated.",
    show_default=True,
)
@click.option(
    "--subscriptions",
    "-s",
    type=int,
    multiple=True,
    default=[],
    help="Subscribe to movements.",
)
@click.pass_context
def create_many_users(ctx, number, subscriptions):
    configure_uri(ctx)
    for i in range(number):
        letters = string.ascii_lowercase
        email = "".join(random.choice(letters) for i in range(12))
        email += "@gmail.com"
        password = lorem.sentence()[:16]
        register(lorem.sentence()[:32], email, password)

    if subscriptions:
        with session_scope() as session:
            user_ids = (
                session.query(User.id)
                .order_by(User.id.desc())
                .limit(number)
                .all()
            )
            for user_id in user_ids:
                for movement_id in subscriptions:
                    subscribe(user_id, movement_id)


@create_many.command(
    name="movements",
    short_help="Create many random movements in the database.",
)
@click.option("--number", "-n", type=int, default=100, show_default=True)
@click.pass_context
def create_many_movements(ctx, number):
    configure_uri(ctx)
    with session_scope() as session:
        for i in range(number):
            movement = create_random_movement()
            session.add(movement)

            # limit max session size
            if i % 1000 == 0 and i != 0:
                session.commit()
                click.echo("Sending 1000 movements")
        click.echo(f"Added {number} random movements")


@count.command(
    name="movements", short_help="Count the movements in the database."
)
@click.pass_context
def count_movements(ctx):
    configure_uri(ctx)
    with session_scope() as session:
        click.echo(session.query(Movement).count())


@count.command(name="users", short_help="Count the users in the database.")
@click.pass_context
def count_users(ctx):
    configure_uri(ctx)
    with session_scope() as session:
        click.echo(session.query(User).count())


@count.command(
    name="subscriptions", short_help="Count the subscriptions of user."
)
@click.argument("user_id", type=int)
@click.pass_context
def count_subscriptions(ctx, user_id):
    configure_uri(ctx)

    # At the present gridt.models.User.current_movements seems to be
    # broken, therefore I am reimplementing it.
    from gridt.models import MovementUserAssociation as MUA

    with session_scope() as session:
        click.echo(
            len(
                session.query(Movement)
                .join(MUA)
                .filter(MUA.movement_id == Movement.id)
                .filter_by(follower_id=user_id, destroyed=None)
                .all()
            )
        )


@count.command(
    name="associations", short_help="Count movement user assocations"
)
@click.pass_context
def count_muas(ctx):
    configure_uri(ctx)
    with session_scope() as session:
        click.echo(session.query(MUA).count())


@create.command(name="user", short_help="Register a user in the database.")
@click.argument("username")
@click.argument("email")
@click.argument("password")
@click.option(
    "--subscriptions",
    "-s",
    default=[],
    multiple=True,
    help="Subscribe to movements",
)
@click.pass_context
def create_user(ctx, username, email, password, subscriptions):
    configure_uri(ctx)
    register(username, email, password)
    click.echo(f"Registering user {username} successfull")

    if subscriptions:
        with session_scope() as session:
            user_id = session.query(User.id).filter_by(email=email).one()[0]
            click.echo(f"Found user id to be '{user_id}'")
            for movement_id in subscriptions:
                subscribe(user_id, movement_id)
                click.echo(f"Subcribed user to movement: {movement_id}")


@cli.command(short_help="Remove the first n movements.")
@click.option(
    "--number", default=10, help="Number of movements to be removed."
)
@click.pass_context
def remove_movements(ctx, number):
    configure_uri(ctx)
    with session_scope() as session:
        to_delete_rows = session.query(Movement.id).limit(number).all()
        to_delete_ids = list(itertools.chain.from_iterable(to_delete_rows))
        click.echo(f"Deleting {len(to_delete_ids)} movements")
        session.query(Movement).filter(Movement.id.in_(to_delete_ids)).delete(
            synchronize_session=False
        )


@create.command(
    name="subscription",
    short_help="Subscribe a user to a series of movements.",
)
@click.argument("user_id")
@click.argument("movements", nargs=-1)
@click.pass_context
def subscribe_user(ctx, user_id, movements):
    configure_uri(ctx)
    for movement_id in movements:
        click.echo(f"Subscribing user '{user_id}' to movement '{movement_id}'")
        subscribe(user_id, movement_id)


if __name__ == "__main__":
    cli()
