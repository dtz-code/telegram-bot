from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from datetime import timedelta
import asyncio

BOT_TOKEN = '7361438445:AAFDVYpvpvCs2vgY4yCCkx3eam0Q3ODIT-o'  # Replace with your actual bot token

message_text = "Hello, this is an automated message!"
image_file_id = None  # Variable to store the image file ID
interval = 5  # Default interval in minutes

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        'Hello! Welcome to your automated bot. '
        'Use /set_message <your message> or send a message with an image or attachment '
        'to set the message that should be sent automatically. '
        'Use /set_interval <minutes> to set the interval, '
        'and /schedule_message to start sending messages.'
    )

async def set_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global message_text, image_file_id

    # Only store the text after the command, removing the command itself
    if len(context.args) > 0:
        message_text = ' '.join(context.args)
    else:
        message_text = ''
        
    image_file_id = None  # Reset the image file ID when a new message is set
    await update.message.reply_text(f'New message set: "{message_text}"')

async def handle_media_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

if __name__ == '__main__':
    # Use the already running event loop
    loop = asyncio.get_event_loop()
    loop.create_task(main())
    loop.run_forever()
