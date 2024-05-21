-- Table to store user information
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT UNIQUE
);

-- Table to store exercise information
CREATE TABLE IF NOT EXISTS exercises (
    exercise_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE
);

-- Table to store workout sessions
CREATE TABLE IF NOT EXISTS sessions (
    session_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    start_time TEXT,
    end_time TEXT,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

-- Table to store sets of exercises
CREATE TABLE IF NOT EXISTS set_exercises (
    set_exercise_id INTEGER PRIMARY KEY AUTOINCREMENT,
    exercise_id INTEGER,
    weight INTEGER,
    FOREIGN KEY (exercise_id) REFERENCES exercises(exercise_id)
);

-- Table to store individual sets
CREATE TABLE IF NOT EXISTS sets (
    set_id INTEGER PRIMARY KEY AUTOINCREMENT,
    set_exercise_id INTEGER,
    reps INTEGER,
    FOREIGN KEY (set_exercise_id) REFERENCES set_exercises(set_exercise_id)
);

-- Table to store the relationship between sessions and sets
CREATE TABLE IF NOT EXISTS session_sets (
    session_set_id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER,
    set_id INTEGER,
    set_number INTEGER,
    FOREIGN KEY (session_id) REFERENCES sessions(session_id),
    FOREIGN KEY (set_id) REFERENCES sets(set_id)
);
