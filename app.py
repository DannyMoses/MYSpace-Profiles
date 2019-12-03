from flask import Flask, request
from flask_pymongo import PyMongo
import requests

import logging

from config import config

app = Flask(__name__)
search_route = config["elasticsearch_route"]

app.config['MONGO_URI'] = "mongodb://{}:{}@{}/{}".format(
				config['mongo_usr'],
				config['mongo_pwd'],
				config['mongo_ip'],
				config['mongo_db']
			)
mongo = PyMongo(app)

# Setup logging
if __name__ != '__main__':
	gunicorn_logger = logging.getLogger('gunicorn.error')
	app.logger.handlers = gunicorn_logger.handlers
	app.logger.setLevel(gunicorn_logger.level)

@app.route("/reset_profiles", methods=["POST"])
def reset():
	app.logger.warning("/reset_profiles called")
	mongo.db.profiles.drop()
	return { "status": "OK" }, 200

# Used to add a user from registration
@app.route('/user', methods=["POST"])
def add_profile():
	app.logger.debug(80*'=')
	app.logger.debug("/ADD_PROFILE()")

	data = request.json

	mongo.db.profiles.insert_one({
		"username" : data["username"],
		"email" : data["email"],
		"following" : [],
		"num_following" : 0,
		"followed_by" : [],
		"num_followed" : 0
	})

	return { "status" : "OK" }, 200

@app.route('/user', methods=["GET"])
def get_profile():
	app.logger.debug(80*'=')
	app.logger.debug("/GET_PROFILE()")
	data = request.json
	usr = mongo.db.profiles.find_one({"username" : data["username"]})

	app.logger.debug(data)

	if not usr:
		return {"status" : "error", "error" : "could not find user" }, 404

	app.logger.debug(usr)

	return {
		"status" : "OK",
		"user" : {
			"email" : usr["email"],
			"followers" : usr["num_followed"],
			"following" : usr["num_following"]
		}
	}, 200

@app.route('/user/posts', methods=["POST"])
def get_posts():
	app.logger.debug(80*'=')
	app.logger.debug("/GET_POSTS()")
	data = request.json

	limit = 50 # default
	if "limit" in data:
		limit = data["limit"]
		if limit > 200:
			limit = 200

	query = {
		"query": {
			"bool": {
				"filter": [
					{ "term": {"username": data['username']} }
				]
			}
		},
		"size": limit
	}

	app.logger.info(query)

	r = requests.get(url=('http://' + search_route + '/posts/_search'), json=query)
	r_json = r.json()

	app.logger.debug(r_json['hits']['hits'])

	results = []
	for search_result in r_json['hits']['hits']:
		results.append(search_result['_id'])
		app.logger.debug(search_result['_id'])

#	if not results:
#		return {"status" : "error", "error" : "Could not find any posts by the specified user" }, 200 #400

	return { "status" : "OK", "items" : results }, 200

@app.route('/user/followers', methods=["POST"])
def get_followers():
	app.logger.debug(80*'=')
	app.logger.debug("/USER/FOLLOWERS()")
	data = request.json
	usr = mongo.db.profiles.find_one({"username" : data["username"]})

	if not usr:
		return { "status" : "error", "error" : "unable to find user" }, 404

	limit = 50 # default
	if "limit" in data:
		limit = data["limit"]
		if limit > 200:
			limit = 200

	usr_f = usr["followed_by"][0:limit]
	
	return { "status" : "OK", "users" : usr_f }, 200

@app.route('/user/following', methods=["POST"])
def get_following():
	app.logger.debug(80*'=')
	app.logger.debug('/USER/FOLLOWING()')
	data = request.json
	usr = mongo.db.profiles.find_one({"username" : data["username"]})

	if not usr:
		return { "status" : "error", "error" : "unable to find user" }, 404

	limit = 50 # default
	if "limit" in data:
		limit = data["limit"]
		if limit > 200:
			limit = 200

	usr_f = usr["following"][0:limit]
	
	return { "status" : "OK", "users" : usr_f }, 200

@app.route('/follow', methods=["POST"])
def follow():
	app.logger.debug(80*'=')
	app.logger.debug('/FOLLOW()')
	data = request.json

	app.logger.debug(data)

	if data['user'] == data['username']:
		return { "status" : "error", "error" : "You cannot follow yourself" }, 200 #400

	user = mongo.db.profiles.find_one({"username" : data["user"]})
	user_followed = mongo.db.profiles.find_one({"username" : data["username"]})

	if not user or not user_followed:
		return { "status" : "error", "error" : "Could not find user" }, 200 #404

	follow = True
	if "follow" in data:
		follow = data["follow"]
		#follow = False
	
	if follow and user_followed['username'] not in user['following']:
		mongo.db.profiles.update_one(
			{ "username" : data["user"] },
			{
				"$inc" : { "num_following" : 1 },
				"$push" : { "following" : data["username"] }
			}
		)
		mongo.db.profiles.update_one(
			{ "username" :  data["username"] },
			{
				"$inc" : { "num_followed" : 1 },
				"$push" : { "followed_by" : data["user"] }
			}
		)
	else:
		mongo.db.profiles.update_one(
			{ "username" : data["user"] },
			{
				"$inc" : { "num_following" : -1 },
				"$pull" : { "following" : data["username"] }
			}
		)
		mongo.db.profiles.update_one(
			{ "username" :  data["username"] },
			{
				"$inc" : { "num_followed" : -1 },
				"$pull" : { "followed_by" : data["user"] }
			}
		)
	
	return { "status" : "OK" }, 200

@app.route('/follow', methods=["GET"])
def get_follow():
	data = request.json
	app.logger.debug(data)

	if data['user'] == data['username']:
		return { "status" : "error", "error" : "You cannot follow yourself" }, 400

	result = mongo.db.profiles.find_one({ "$and": [
		{ "username": data['user'] },
		{ "following": data['username'] }
	]})

	if result:
		return { "status" : "OK", "follow" : True }, 200
	else:
		return { "status" : "OK", "follow" : False }, 200

#@app.route('/user_media', methods=["POST"])
#def user_media():
#	data = request.json
#	app.logger.debug(data)
#	
#	result = mongo.db.profiles.find_one({ "username" : data['user'] })['media']
#
#	return { "status" : "OK", "user_media" : result }, 200
#
#@app.route('/add_media', methods=["POST"])
#def add_media():
#	data = request.json
#	app.logger.debug(data)
#	
#	mongo.db.profiles.update_one( { "username" : data["user"] },
#					{
#					"$push" : { "media" : data["media_id"] }
#					}
#	)
#
#	return { "status" : "OK" }, 200
#
#@app.route('/user/media', methods=["DELETE"])
#def delete_media():
#	data = request.json
#	app.logger.debug(data)
#	print(data)
#	
#	mongo.db.profiles.update_one( { "username" : data["user"] },
#					{
#					"$pullAll" : { "media" : data["media"] }
#					}
#	)
#	print('finished')
#
#	return { "status" : "OK" }, 200
#
