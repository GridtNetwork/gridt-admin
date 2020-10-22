#! /usr/bin/env python
import sys
import os
import click
import lorem
from sqlalchemy import create_engine
from gridt.db import Session, Base
from gridt.models import Movement

session = None


def check_session():
    if not Session:
        click.secho("Session not initialized!", fg="red")
        sys.exit(1)


@click.group()
@click.option(
    "--uri", help="URI of the database, overwrites environment variable ADMIN_DB_URI"
)
def cli(uri):
    if not uri:
        uri = os.environ.get("ADMIN_DB_URI")
        if not uri:
            click.secho("No database URI provided, exiting.")
    engine = create_engine(uri)
    session = Session.configure(bind=engine)


def create_random_movement():
    interval = random.choice(["daily", "weekly"])
    movement = Movement(
        lorem.sentence(), interval, lorem.paragraph(), lorem.paragraph()
    )
    return movement


@cli.command()
@click.option("--number", "-n", type=int, default=100)
def create_many_movements(number):
    check_session()

    for i in range(number):
        movement = create_random_movement()
        session.add(movement)

        # limit max session size
        if i % 1000:
            session.commit()

    session.commit()


if __name__ == "__main__":
    cli()
