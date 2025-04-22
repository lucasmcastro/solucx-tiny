# solucx-tiny
1. Enter project folder
```
$ cd solucx-tiny/
```
2. Create virtual environment (venv)
```
python3 -m venv venv
```
3. Activate venv
```
$ source venv/bin/activate
```
4. Install requirements
```
$ pip3 install -r requirements.txt
```
5. Copy .env-example to .env
```
$ cp .env-example .env
```
6. Set the right config params inside .env file
7. Set your ngrok to a static domain and port 8000
```
ngrok http --url=your-static-ngrok-url.ngrok-free.app 8000
```
8. Run the app 
```
$ python3 app.py
```