#! /usr/bin/env python

import sys
import os
import random
from functools import wraps

import click
import lorem

from sqlalchemy import create_engine

from gridt.db import Session, Base
from gridt.controllers.helpers import session_scope
from gridt.models import Movement
from gridt.controllers.user import register


@click.group()
@click.option(
    "--uri",
    default=None,
    help="URI of the database, overwrites environment variable ADMIN_DB_URI",
)
@click.pass_context
def cli(ctx, uri):
    ctx.ensure_object(dict)

    if not uri:
        uri = os.environ.get("ADMIN_DB_URI")

        if not uri:
            click.secho("No database URI provided, exiting.")
        else:
            click.echo("Using URI from environment")
    else:
        click.echo("Using URI from command line")

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


@cli.command(help="Create the required tables in the database.")
@click.pass_context
def initialize_database(ctx):
    Base.metadata.create_all(ctx.obj["engine"])


@cli.command(help="Create many random movements in the database.")
@click.option("--number", "-n", type=int, default=100)
def create_many_movements(number):
    with session_scope() as session:
        for i in range(number):
            movement = create_random_movement()
            session.add(movement)

            # limit max session size
            if i % 1000:
                session.commit()
                click.echo('Sending 1000 movements')
        click.echo(f'Added {number} random movements')


@cli.command(help="Count the movements in the database.")
def count_movements():
    with session_scope() as session:
        click.echo(session.query(Movement).count())


@cli.command(help="Register a user in the database.")
@click.argument('username')
@click.argument('email')
@click.argument('password')
def register_user(username, email, password):
    register(username, email, password)
    click.echo(f'Registering user {username} successfull')

if __name__ == "__main__":
    cli()
