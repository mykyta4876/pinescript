from app import app, init_background_tasks

init_background_tasks()

if __name__ == "__main__":
    app.run()