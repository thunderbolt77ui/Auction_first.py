import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import sqlite3

TOKEN = "8175464344:AAEYCl2B5r-ZW4porLajwL2XVQ_lYws92Go"
CHANNEL_ID = "@CV_giveawayParticipating"

bot = telebot.TeleBot(TOKEN)

# Database setup
conn = sqlite3.connect("auction.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS auctions 
                  (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                   user_id INTEGER, username TEXT, 
                   pokemon TEXT, price INTEGER, highest_bid INTEGER, highest_bidder TEXT)''')
conn.commit()

# Command to start auction
@bot.message_handler(commands=["sell"])
def sell_pokemon(message):
    bot.send_message(message.chat.id, "Send your Pokémon name and starting price in this format:\n\n`Pikachu, 1000`", parse_mode="Markdown")

@bot.message_handler(func=lambda message: "," in message.text)
def add_auction(message):
    try:
        user_id = message.from_user.id
        username = message.from_user.username
        pokemon, price = message.text.split(",")
        price = int(price.strip())

        cursor.execute("INSERT INTO auctions (user_id, username, pokemon, price, highest_bid, highest_bidder) VALUES (?, ?, ?, ?, ?, ?)",
                       (user_id, username, pokemon.strip(), price, price, username))
        conn.commit()

        auction_id = cursor.lastrowid

        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("Place Bid", callback_data=f"bid_{auction_id}"))

        auction_text = f"🔥 **{pokemon.strip()}** is up for auction!\n💰 Starting Price: {price}\n👤 Seller: @{username}\n\n💬 Tap below to place a bid!"
        bot.send_message(message.chat.id, "Auction created successfully!")
        bot.send_message(CHANNEL_ID, auction_text, reply_markup=markup)

    except Exception as e:
        bot.send_message(message.chat.id, "Error: Invalid format! Use `Pikachu, 1000`")

# Handling bids
@bot.callback_query_handler(func=lambda call: call.data.startswith("bid_"))
def place_bid(call):
    auction_id = int(call.data.split("_")[1])

    msg = bot.send_message(call.message.chat.id, "Enter your bid amount:")
    bot.register_next_step_handler(msg, process_bid, auction_id, call.from_user)

def process_bid(message, auction_id, user):
    try:
        bid_amount = int(message.text)

        cursor.execute("SELECT highest_bid FROM auctions WHERE id=?", (auction_id,))
        result = cursor.fetchone()

        if result and bid_amount > result[0]:
            cursor.execute("UPDATE auctions SET highest_bid=?, highest_bidder=? WHERE id=?",
                           (bid_amount, user.username, auction_id))
            conn.commit()

            bot.send_message(message.chat.id, f"✅ Bid placed: {bid_amount}")
            
            cursor.execute("SELECT pokemon FROM auctions WHERE id=?", (auction_id,))
            pokemon = cursor.fetchone()[0]
            updated_text = f"🔥 **{pokemon}** is up for auction!\n💰 Highest Bid: {bid_amount}\n👤 Highest Bidder: @{user.username}"

            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("Place Bid", callback_data=f"bid_{auction_id}"))
            bot.send_message(CHANNEL_ID, updated_text, reply_markup=markup)

        else:
            bot.send_message(message.chat.id, "⚠️ Bid must be higher than the current highest bid.")

    except ValueError:
        bot.send_message(message.chat.id, "❌ Invalid bid amount! Please enter a number.")

bot.polling()