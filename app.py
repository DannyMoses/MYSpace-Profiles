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

# Used to add a user from registration
@app.route('/user', methods=["POST"])
def add_profile():
	print(80*'=')
	print("/ADD_PROFILE()")

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
	print(80*'=')
	print("/GET_PROFILE()")
	data = request.json
	usr = mongo.db.profiles.find_one({"username" : data["username"]})

	if not usr:
		return {"status" : "error", "message" : "could not find user" }, 200 #400

	return {
		"status" : "OK",
		"user" : {
			"email" : usr["email"],
			"followers" : usr["num_following"],
			"following" : usr["num_followed"]
		}
	}, 200

@app.route('/user/posts', methods=["GET"])
def get_posts():
	print(80*'=')
	print("/GET_POSTS()")
	data = request.json

	limit = 50 # default
	if "limit" in data:
		limit = data["limit"]
		if limit > 200:
			limit = 200

	query = {
		"query": {
			"bool": {
				"filter": {
					"term": {"username": data['username']}
				}
			}
		},
		"size": limit
	}

	r = requests.get(url=('http://' + search_route + '/posts/_search'), json=query)
	r_json = r.json()

	app.logger.debug(r_json['hits']['hits'])

	results = []
	for search_result in r_json['hits']['hits']:
		results.append(search_result['_id'])
		app.logger.debug(search_result['_id'])

	if not results:
		return {"status" : "error", "message" : "Could not find any posts by the specified user" }, 200 #400

	return { "status" : "OK", "item" : results }, 200

@app.route('/user/followers', methods=["GET"])
def get_followers():
	print(80*'=')
	print("/USER/FOLLOWERS()")
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

@app.route('/user/following', methods=["GET"])
def get_following():
	print(80*'=')
	print('/USER/FOLLOWING()')
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
	print(80*'=')
	print('/FOLLOW()')
	data = request.json

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
				{ "$inc" : { "num_following" : 1 } },
				{ "$push" : { "following" : data["username"] } }
			}
		)
		mongo.db.profiles.update_one(
			{ "username" :  data["username"] },
			{
				{ "$inc" : { "num_followed" : 1 } },
				{ "$push" : { "followed_by" : data["user"] } }
			}
		)
	else:
		mongo.db.profiles.update_one(
			{ "username" : data["user"] },
			{
				{ "$inc" : { "num_following" : -1 } },
				{ "$pull" : { "following" : data["username"] } }
			}
		)
		mongo.db.profiles.update_one(
			{ "username" :  data["username"] },
			{
				{ "$inc" : { "num_followed" : -1 } },
				{ "$pull" : { "followed_by" : data["user"] } }
			}
		)
	
	return { "status" : "OK" }, 200

