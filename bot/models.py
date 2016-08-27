from peewee import *
from playhouse.sqlite_ext import SqliteExtDatabase
import datetime

db_schema_version = 1
db = SqliteExtDatabase('bot.db')

class BaseModel(Model):
	class Meta:
		database = db

class User(BaseModel):
	username = CharField(unique=True)

	@staticmethod
	def create_user(name):
		try:
			user = User.create(username=name)
			Location.create(user=user, start_lat=0, start_lng=0, lat=0, lng=0)
		except IntegrityError:
			None


class Location(BaseModel):
	user = ForeignKeyField(User, related_name='locations', primary_key=True)
	start_lat = DoubleField()
	start_lng = DoubleField()
	lat = DoubleField()
	lng = DoubleField()

	@staticmethod
	def check_location(name, lat, lng):
		locations = Location.select().where(
			Location.user == User.select().where(User.username == name), 
			Location.start_lat == lat,
			Location.start_lng == lng
		).count()

		if locations == 0:
			q = Location.update(
					start_lat = lat,
					start_lng = lng,
					lat = lat,
					lng = lng,
				).where(
					Location.user == User.select().where(User.username == name)
				)
			q.execute()

			return False

		return True

	@staticmethod
	def get_location(name):
		locations = Location.select().where(
			Location.user == User.select().where(User.username == name)
		).get()

		return locations.lat, locations.lng

	@staticmethod
	def set_location(name, lat, lng):
		q = Location.update(
				lat = lat,
				lng = lng,
			).where(
				Location.user == User.select().where(User.username == name)
			)
		q.execute()


class Catch(BaseModel):
	user = ForeignKeyField(User, related_name='catchs')
	encounter_id = CharField(primary_key=True, max_length=50)
	created_date = DateTimeField(default=datetime.datetime.now)

class Pokestop(BaseModel):
	user = ForeignKeyField(User, related_name='stops')
	created_date = DateTimeField(default=datetime.datetime.now)
			
def init_db():
	db.connect()
	db.create_tables([User, Location, Catch, Pokestop], safe=True)
	db.close()
