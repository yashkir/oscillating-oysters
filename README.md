![Logo](banner.png)

# Oscillating Oysters - TwentyTwentyMUD

You have gone back in time to the beginnings of the internet, can you find
your way back to 2020 with your friends?

## Installation

Quickstart:
```
cd twentytwentymud/
./QUICKSTART.sh
```
Using `docker-compose`, this will simply migrate, load fixtures, and start. 
```
docker-compose run --rm web python manage.py migrate
./load_data.sh
docker-compose up
```
The app should be running on localhost:8000 (or whatever ip docker is setup for).
Two users have already been created (username:password):
```
root:root
oyster:oysteroyster
```

New users can also be created from the login. Network play works and can be
tested by logging in a second user in an incognito window.

## Gameplay

Type `help` for a list of commands. You can move with `go ROOM` or `go NUMBER`.
Use `say MESSAGE` or `send MESSAGE` to talk to others. Some commands may be
hidden.

## Notes

Extras used:
- xterm.js (front-end terminal)
- ansiwrap (wrapping colored text in terminal)
- channels (sockets, etc.)

Other useful commands:
```
docker-compose run --rm web python manage.py createsuperuser
docker-compose up -d
```
