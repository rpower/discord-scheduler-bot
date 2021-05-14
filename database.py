import json
import sqlalchemy as db
from sqlalchemy.orm import declarative_base, sessionmaker, Session
import datetime

now = datetime.datetime.now()

with open('credentials.json') as credentials_file:
    credentials = json.loads(credentials_file.read())

engine = db.create_engine(credentials['sql_details']['path_to_db'])

Base = declarative_base()


class Event(Base):
    __tablename__ = credentials['sql_details']['table_name']

    id = db.Column(db.BigInteger, primary_key=True)
    event = db.Column(db.String)
    attendees = db.Column(db.String)
    datetime = db.Column(db.DateTime)
    reminder_time = db.Column(db.DateTime)
    creator = db.Column(db.String)
    server = db.Column(db.String)
    channel = db.Column(db.String)
    reminded_flag = db.Column(db.Boolean)

    def __repr__(self):
        return "<Event(id='%s', event='%s', attendees='%s', datetime='%s', reminder_time='%s', creator='%s', " \
               "server='%s', channel='%s', reminded_flag='%s')>" % (
                   self.id, self.event, self.attendees, self.datetime, self.reminder_time, self.creator, self.server,
                   self.channel, self.reminded_flag)


def create_session():
    original_session = sessionmaker()
    original_session.configure(bind=engine)
    return original_session()


def commit_and_end_session(session):
    session.commit()
    session.close()


def add_new_event(event_id, event, attendees, event_date_time, reminder_time, creator, server, channel):
    session = create_session()

    # Create new entry
    new_event = Event(
        id = event_id,
        event = event,
        attendees = attendees,
        datetime = event_date_time,
        reminder_time = reminder_time,
        creator = creator,
        server = server,
        channel = channel,
        reminded_flag=False
    )
    session.add(new_event)
    commit_and_end_session(session)


def get_upcoming_events(server):
    session = create_session()

    s = db.select(
        Event.id, Event.event, Event.attendees, Event.datetime
    ).where(
        Event.server == server, Event.datetime > now
    )
    result = session.execute(s)
    return result


def check_single_event_exists(event_id, creator, server):
    session = create_session()

    s = db.select(
        Event.id, Event.creator, Event.server
    ).where(
        Event.id == event_id, Event.creator == creator, Event.server == server
    )
    result = session.execute(s).scalar()
    return result


def delete_single_event(event_id, creator, server):
    session = create_session()

    d = db.delete(Event).where(
        Event.id == event_id, Event.creator == creator, Event.server == server
    )
    session.execute(d)
    commit_and_end_session(session)


def get_events_to_remind():
    session = create_session()

    s = db.select(Event).where(
        datetime.datetime.now() > Event.reminder_time,
        Event.reminded_flag == False
    )
    result = session.execute(s).all()
    return result

def mark_events_as_reminded(event_id):
    session = create_session()

    u = db.update(Event).where(
        Event.id == event_id
    ).values(
        reminded_flag = True
    )

    session.execute(u)
    commit_and_end_session(session)
