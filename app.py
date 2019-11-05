from flask import Flask, request
from flask_pymongo import PyMongo
import requests

import logging

from config import config

app = Flask(__name__)
app.config["MONGO_URI"] = "mongodb://localhost:27017/Profiles"
mongo = PyMongo(app)
search_route = config["elasticsearch_route"]

# Setup logging
if __name__ != '__main__':
	gunicorn_logger = logging.getLogger('gunicorn.error')
	app.logger.handlers = gunicorn_logger.handlers
	app.logger.setLevel(gunicorn_logger.level)

@app.route("/reset_profiles", methods=["POST"])
def reset():
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

	if not usr:
		return {"status" : "error", "message" : "could not find user" }, 200 #400

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
					{ "match": {"username": data['username']} }
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
#		return {"status" : "error", "message" : "Could not find any posts by the specified user" }, 200 #400

	return { "status" : "OK", "items" : results }, 200

@app.route('/user/followers', methods=["POST"])
def get_followers():
	app.logger.debug(80*'=')
	app.logger.debug("/USER/FOLLOWERS()")
	data = request.json
	usr = mongo.db.profiles.find_one({"username" : data["username"]})

	if not usr:
		return { "status" : "error", "message" : "unable to find user" }, 200 #400

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
		return { "status" : "error", "message" : "unable to find user" }, 200 #400

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

	user = mongo.db.profiles.find_one({"username" : data["user"]})
	user_followed = mongo.db.profiles.find_one({"username" : data["username"]})

	if not user or not user_followed:
		return { "status" : "error", "message" : "could not find user" }, 200 #400

	follow = True
	if "follow" in data:
		follow = data["follow"]
		#follow = False
	
	if follow:
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
            
