from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from datetime import timedelta
import asyncio
import os

# Load bot token and password from environment variables
BOT_TOKEN = os.getenv('7361438445:AAFDVYpvpvCs2vgY4yCCkx3eam0Q3ODIT-o')  # Replace with your actual bot token
PASSWORD = os.getenv('selmanBOT123321')  # Replace with your actual password

# Variables to store bot settings
message_text = "Hello, this is an automated message!"
image_file_id = None  # Variable to store the image file ID
interval = 5  # Default interval in minutes
authorized_user_id = None  # Store the ID of the user who is authorized

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Display inline keyboard to enter password
    keyboard = [[InlineKeyboardButton("Enter Password", callback_data='enter_password')]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        'Welcome to the automated bot. Please enter the password using the button below.',
        reply_markup=reply_markup
    )

async def enter_password_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    # Ask for password entry in private chat
    await query.message.reply_text('Please enter your password in this private chat using the format /password <your_password>.')

async def password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global authorized_user_id

    # Ensure the password is entered in a private chat
    if update.message.chat.type != 'private':
        await update.message.reply_text('Please enter the password in a private chat with the bot.')
        return

    # Get the entered password
    if len(context.args) > 0 and context.args[0] == PASSWORD:
        authorized_user_id = update.message.from_user.id
        await update.message.reply_text(
            'Password accepted. You are now authorized to use the bot commands.'
        )
    else:
        await update.message.reply_text('Incorrect password. Please try again.')

async def check_authorization(update: Update):
    global authorized_user_id
    if update.message.from_user.id != authorized_user_id:
        await update.message.reply_text('You are not authorized to use this command. Please enter the correct password in a private chat using /password.')
        return False
    return True

async def set_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_authorization(update):
        return

    global message_text, image_file_id

    # Store only the text after the command
    if len(context.args) > 0:
        message_text = ' '.join(context.args)
    else:
        message_text = ''
        
    image_file_id = None  # Reset the image file ID when a new message is set
    await update.message.reply_text(f'New message set: "{message_text}"')

async def handle_media_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_authorization(update):
        return

    global message_text, image_file_id
    # Extract only the caption without the '/set_message' command
    if update.message.caption and update.message.caption.startswith('/set_message'):
        message_text = update.message.caption.split(' ', 1)[1] if ' ' in update.message.caption else ''
    else:
        message_text = update.message.caption if update.message.caption else "Automated message"
    
    # Check if the message contains a photo
    if update.message.photo:
        image_file_id = update.message.photo[-1].file_id  # Use the highest resolution of the image
        await update.message.reply_text('Image saved.')
    else:
        await update.message.reply_text('No image found. Please send an image to save it.')

async def set_interval(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_authorization(update):
        return

    global interval
    try:
        interval = int(context.args[0])
        await update.message.reply_text(f'Interval set to {interval} minutes.')
    except (IndexError, ValueError):
        await update.message.reply_text('Please provide a valid number for the interval in minutes.')

async def send_message(context: ContextTypes.DEFAULT_TYPE):
    chat_id = context.job.data  # Use the passed chat ID from the scheduled job
    if image_file_id:
        # Send the image if an image file ID is set
        await context.bot.send_photo(chat_id=chat_id, photo=image_file_id, caption=message_text)
    else:
        # Send only the message if no image file ID is set
        await context.bot.send_message(chat_id=chat_id, text=message_text)

async def schedule_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_authorization(update):
        return

    chat_id = update.effective_chat.id

    # Remove all existing scheduled jobs for this group
    jobs = context.job_queue.get_jobs_by_name(str(chat_id))
    for job in jobs:
        job.schedule_removal()

    # Send the first message immediately
    if image_file_id:
        await context.bot.send_photo(chat_id=chat_id, photo=image_file_id, caption=message_text)
    else:
        await context.bot.send_message(chat_id=chat_id, text=message_text)

    # Schedule the message sending at the defined interval
    context.job_queue.run_repeating(send_message, interval=timedelta(minutes=interval), data=chat_id, name=str(chat_id))
    await update.message.reply_text(f'Automated messages scheduled every {interval} minutes.')

async def stop_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_authorization(update):
        return

    chat_id = update.effective_chat.id

    # Remove all scheduled jobs for this group
    jobs = context.job_queue.get_jobs_by_name(str(chat_id))
    if jobs:
        for job in jobs:
            job.schedule_removal()
        await update.message.reply_text('Automated messages stopped.')
    else:
        await update.message.reply_text('No scheduled messages.')

async def main():
    # Build the application with a JobQueue
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(enter_password_callback, pattern='enter_password'))
    application.add_handler(CommandHandler("password", password))
    application.add_handler(CommandHandler("set_message", set_message))
    application.add_handler(MessageHandler(filters.PHOTO, handle_media_message))  # Filter for photos
    application.add_handler(CommandHandler("set_interval", set_interval))
    application.add_handler(CommandHandler("schedule_message", schedule_message))
    application.add_handler(CommandHandler("stop_message", stop_message))

    # Start the application and polling loop
    await application.initialize()
    await application.start()
    await application.job_queue.start()
    print("Bot is now running...")
    await application.updater.start_polling()
    await application.idle()  # Keeps the bot running until manually stopped

if __name__ == '__main__':
    # Use the already running event loop
    loop = asyncio.get_event_loop()
    loop.create_task(main())
    loop.run_forever()
