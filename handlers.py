import logging
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext, ConversationHandler
from db import get_connection, init_db, DB_PATH, SCHEMA_PATH

logger = logging.getLogger(__name__)

# Initialize the database
init_db(DB_PATH, SCHEMA_PATH)

SESSIONS = {}
LAST_ACTION = {}
TIMEOUT = timedelta(hours=2)

CHOOSING_EXERCISE, ENTERING_WEIGHT, ENTERING_REPS, CONTINUE_SET = range(4)

async def start(update: Update, context: CallbackContext) -> int:
    """Starts a workout session for the user and stores the initial session data."""
    user_id = update.message.from_user.id
    username = update.message.from_user.username
    logger.info(f"Starting session for user_id: {user_id}, username: {username}")

    with get_connection(DB_PATH) as conn:
        c = conn.cursor()
        c.execute('INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)', (user_id, username))
        conn.commit()
        c.execute('INSERT INTO sessions (user_id, start_time) VALUES (?, ?)', (user_id, datetime.now().isoformat()))
        conn.commit()
        session_id = c.lastrowid

    SESSIONS[user_id] = {'session_id': session_id, 'set_count': 0}
    LAST_ACTION[user_id] = None
    await update.message.reply_text("Workout session started! Please choose an exercise.")
    return CHOOSING_EXERCISE

async def choose_exercise(update: Update, context: CallbackContext) -> int:
    """Logs the chosen exercise and prompts for weight."""
    user_id = update.message.from_user.id
    exercise_name = update.message.text
    logger.info(f"User {user_id} chose exercise: {exercise_name}")

    with get_connection(DB_PATH) as conn:
        c = conn.cursor()
        c.execute('INSERT OR IGNORE INTO exercises (name) VALUES (?)', (exercise_name,))
        conn.commit()
        c.execute('SELECT exercise_id FROM exercises WHERE name = ?', (exercise_name,))
        exercise_id = c.fetchone()[0]

    context.user_data['current_exercise_id'] = exercise_id
    LAST_ACTION[user_id] = {'action': 'choose_exercise', 'exercise_name': exercise_name}
    await update.message.reply_text(f"Chosen exercise: {exercise_name}. Now enter the weight (kg).")
    return ENTERING_WEIGHT

async def enter_weight(update: Update, context: CallbackContext) -> int:
    """Logs the weight and prompts for reps."""
    user_id = update.message.from_user.id
    weight = update.message.text
    logger.info(f"User {user_id} entered weight: {weight}")

    if not weight.isdigit():
        await update.message.reply_text("Please enter a valid weight in kg.")
        return ENTERING_WEIGHT

    context.user_data['current_weight'] = weight
    LAST_ACTION[user_id] = {'action': 'enter_weight', 'weight': weight}
    await update.message.reply_text(f"Weight: {weight}kg. Now enter the number of reps.")
    return ENTERING_REPS

async def enter_reps(update: Update, context: CallbackContext) -> int:
    """Logs the reps for the chosen exercise and weight."""
    user_id = update.message.from_user.id
    reps = update.message.text
    logger.info(f"User {user_id} entered reps: {reps}")

    if not reps.isdigit():
        await update.message.reply_text("Please enter a valid number of reps.")
        return ENTERING_REPS

    exercise_id = context.user_data.get('current_exercise_id')
    weight = context.user_data.get('current_weight')
    session_id = SESSIONS[user_id]['session_id']
    set_count = SESSIONS[user_id]['set_count'] + 1
    SESSIONS[user_id]['set_count'] = set_count

    with get_connection(DB_PATH) as conn:
        c = conn.cursor()
        c.execute('INSERT INTO set_exercises (exercise_id, weight) VALUES (?, ?)', (exercise_id, weight))
        conn.commit()
        set_exercise_id = c.lastrowid
        c.execute('INSERT INTO sets (set_exercise_id, reps) VALUES (?, ?)', (set_exercise_id, reps))
        conn.commit()
        set_id = c.lastrowid
        c.execute('INSERT INTO session_sets (session_id, set_id, set_number) VALUES (?, ?, ?)', (session_id, set_id, set_count))
        conn.commit()

    LAST_ACTION[user_id] = {'action': 'enter_reps', 'set_id': set_id}

    keyboard = [
        [
            InlineKeyboardButton("Enter Next Set", callback_data='next_set'),
            InlineKeyboardButton("Update Weight", callback_data='update_weight'),
            InlineKeyboardButton("Choose Another Exercise", callback_data='choose_exercise')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(f"Logged: {weight}kg x {reps} reps. Enter another set or update weight.", reply_markup=reply_markup)
    return CONTINUE_SET

async def next_set(update: Update, context: CallbackContext) -> int:
    """Handles entering the reps for the next set with the same weight."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(text="Enter reps for the next set.")
    return ENTERING_REPS

async def update_weight(update: Update, context: CallbackContext) -> int:
    """Handles updating the weight."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(text="Enter new weight.")
    return ENTERING_WEIGHT

async def choose_another_exercise(update: Update, context: CallbackContext) -> int:
    """Handles choosing another exercise."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(text="Please choose another exercise.")
    return CHOOSING_EXERCISE

async def button_handler(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    await query.answer()

    if query.data == 'next_set':
        return await next_set(update, context)
    elif query.data == 'update_weight':
        return await update_weight(update, context)
    elif query.data == 'choose_exercise':
        return await choose_another_exercise(update, context)

    return ConversationHandler.END

async def undo(update: Update, context: CallbackContext) -> int:
    """Undo the last action performed by the user."""
    user_id = update.message.from_user.id
    last_action = LAST_ACTION.get(user_id)

    if not last_action:
        await update.message.reply_text("No action to undo.")
        return ConversationHandler.END

    action = last_action['action']

    with get_connection(DB_PATH) as conn:
        c = conn.cursor()

        if action == 'choose_exercise':
            exercise_name = last_action['exercise_name']
            logger.info(f"Undoing choose_exercise: {exercise_name}")
            # No need to delete the exercise since it might be used in other sessions

        elif action == 'enter_weight':
            weight = last_action['weight']
            logger.info(f"Undoing enter_weight: {weight}")
            context.user_data.pop('current_weight', None)
            context.user_data.pop('current_exercise_id', None)

        elif action == 'enter_reps':
            set_id = last_action['set_id']
            logger.info(f"Undoing enter_reps: set_id {set_id}")
            c.execute('DELETE FROM session_sets WHERE set_id = ?', (set_id,))
            c.execute('DELETE FROM sets WHERE set_id = ?', (set_id,))
            conn.commit()
            SESSIONS[user_id]['set_count'] -= 1

    LAST_ACTION[user_id] = None
    await update.message.reply_text("Last action undone.")
    return CHOOSING_EXERCISE

async def end(update: Update, context: CallbackContext) -> int:
    """Ends the user's workout session and saves the data to the database."""
    user_id = update.message.from_user.id
    if user_id not in SESSIONS:
        await update.message.reply_text("No active workout session found.")
        return ConversationHandler.END

    session_id = SESSIONS.pop(user_id)['session_id']
    with get_connection(DB_PATH) as conn:
        c = conn.cursor()
        c.execute('UPDATE sessions SET end_time = ? WHERE session_id = ?', (datetime.now().isoformat(), session_id))
        conn.commit()

    await update.message.reply_text("Workout session ended! Data saved.")
    logger.info(f"Session ended for user_id: {user_id}")
    return ConversationHandler.END

async def cancel(update: Update, context: CallbackContext) -> int:
    """Cancels the current operation."""
    await update.message.reply_text('Operation cancelled.')
    logger.info("Operation cancelled by user")
    return ConversationHandler.END

async def check_timeout(context: CallbackContext) -> None:
    """Checks for sessions that have timed out and ends them."""
    now = datetime.now().isoformat()
    for user_id, session in list(SESSIONS.items()):
        if 'last_entry_time' in session and datetime.fromisoformat(session['last_entry_time']) + TIMEOUT < datetime.fromisoformat(now):
            await context.bot.send_message(user_id, "Session timed out.")
            await end_session(user_id, context)

async def end_session(user_id, context: CallbackContext) -> dict:
    """Ends a user's session due to timeout and saves the data to the database."""
    session_id = SESSIONS.pop(user_id)['session_id']
    with get_connection(DB_PATH) as conn:
        c = conn.cursor()
        c.execute('UPDATE sessions SET end_time = ? WHERE session_id = ?', (datetime.now().isoformat(), session_id))
        conn.commit()

    await context.bot.send_message(user_id, "Workout session ended! Data saved.")
    logger.info(f"Session timed out and ended for user_id: {user_id}")
    return {'session_id': session_id}
