#!/bin/sh

git push
git push heroku master

heroku ps:scale web=1
heroku open
