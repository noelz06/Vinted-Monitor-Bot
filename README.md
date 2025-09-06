# 🤖 Vinted Monitor Bot

A fast and efficient Vinted monitoring bot that tracks items and sends notifications via Telegram. **No proxies required** - runs smoothly with intelligent rate limiting and session management.

![Pyth## 🆘 Support

Having issues? Get help here:
- 🐛 **GitHub Issues**: Report bugs or request features via [GitHub Issues](https://github.com/noelz06/vinted-monitor-bot/issues)
- 👤 **GitHub**: Contact me directly [@noelz06](https://github.com/noelz06)
- 💬 **Discord**: Reach out on Discord **noeel_1122**

### 🔍 Troubleshooting

If the bot crashes or behaves unexpectedly, **always check the log file** (`vinted_bot.log`) first - it contains detailed error information that will help identify the issue. The log file is created in the same directory as the bot.

---

⭐ **Star this repo if you found it helpful!** ⭐(https://img.shields.io/badge/Python-3.8%2B-blue)
![License](https://img.shields.io/badge/License-MIT-green)
![Status](https://img.shields.io/badge/Status-Production%20Ready-brightgreen)

## ✨ Features

- 🚀 **Fast & Efficient** - No proxies needed, intelligent session management
- 📦 **Minimal Dependencies** - Only requires 1 pip install (aiohttp)
- 🔍 **Smart Filtering** - Search by category (Clothing/Other), gender, and sizes
- 🌍 **Multi-Country Support** - Works with any Vinted country (.hu, .de, .fr, .com, .es)
- 📱 **Telegram Integration** - Real-time notifications with rich formatting
- 🎯 **Duplicate Prevention** - Never get the same item notification twice
- ⚡ **Rate Limiting** - Built-in protection against API limits
- 🔧 **Easy Setup** - Interactive configuration wizard
- 📊 **Debug Logging** - Full request logging for transparency

## 🛠️ Quick Setup

### Prerequisites
- Python 3.8 or higher
- A Telegram bot token (get one from [@BotFather](https://t.me/botfather))
- Your Telegram Chat ID (get it from [@userinfobot](https://t.me/userinfobot))

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/noelz06/vinted-monitor-bot.git
   cd vinted-monitor-bot
   ```

2. **Install dependencies (just one!)**
   ```bash
   pip install aiohttp
   ```
   *That's it! Only 1 package needed - the rest uses Python's built-in modules.*

3. **Run the bot**
   ```bash
   python vintedbot.py
   ```

4. **Follow the interactive setup**
   - Enter your Telegram bot token
   - Choose your country
   - Add your first search

That's it! 🎉

## 🎯 How It Works

### First Run
When you run the bot for the first time, it will guide you through the setup:

```
🎉 Welcome to Vinted Monitor Bot Setup!
========================================
🤖 Enter your Telegram Bot Token: YOUR_TOKEN_HERE
🌍 Select country:
🇭🇺 1. Hungary (.hu)
🇩🇪 2. Germany (.de)
🇫🇷 3. France (.fr)
🇬🇧 4. UK/International (.com)
🇪🇸 5. Spain (.es)
Choose (1-5): 1
```

### Adding Searches
The bot supports two types of searches:

#### 1. **Clothing Items**
- Specify gender (Men/Women)
- Filter by sizes (S, M, L, XL, etc.)
- Perfect for fashion items

#### 2. **Other Items**
- No size or gender filtering
- Great for electronics, accessories, etc.

### Example Search Setup
```
📦 Select category:
1. Clothing
2. Other
Choose (1-2): 1

🔍 Search query (e.g., 'ralph lauren'): nike air max
💬 Telegram Chat ID: 123456789
📏 Sizes (comma-separated, e.g., 'S,M,L' or press Enter for any): 42,43,44

👔 Select gender:
1. Men
2. Women
Choose (1-2): 1
```

## 📱 Telegram Notifications

You'll receive beautifully formatted notifications for each new item:

```
Nike Air Max 90
💰 Price: 45 EUR
📏 Size: 42
🏷️ Brand: Nike
👤 Seller: john_doe
🔗 View Item
📸 Photo
```

## ⚙️ Configuration

The bot stores everything in `config.json`:

```json
{
  "telegram_token": "YOUR_BOT_TOKEN",
  "country_code": ".hu",
  "searches": [
    {
      "chat_id": "123456789",
      "query": "nike air max",
      "size_titles": ["42", "43", "44"],
      "category": "Clothing",
      "gender": "Men"
    }
  ]
}
```

## 🚀 Performance & Speed

### Why No Proxies?
- **Intelligent Rate Limiting**: Built-in protection prevents API blocks
- **Smart Session Management**: Efficient cookie handling and connection pooling
- **Request Optimization**: Only 20 items per search for faster processing
- **Async Operations**: Non-blocking HTTP requests for maximum speed

### Monitoring Frequency
- Checks every **5 minutes** by default
- Processes all searches simultaneously
- Immediate Telegram notifications

## 🛡️ Anti-Detection Features

- **Human-like Headers**: Mimics real browser requests
- **Random Delays**: Prevents pattern detection
- **Cookie Management**: Maintains session persistence
- **Error Handling**: Graceful recovery from rate limits

## 🎨 Menu System

```
📋 Current searches (1):
==================================================
1. Search: nike air max
   💬 Chat ID: 123456789
   🔍 Query: nike air max
   📦 Category: Clothing
   👔 Gender: Men
   📏 Sizes: 42, 43, 44
   ✅ Enabled: True
   🔢 Items found: 0

🌍 Current country: .hu

What would you like to do?
1. ➕ Add new search
2. ❌ Remove search
3. 🌍 Change country
4. 🚀 Start monitoring
5. 🚪 Exit
```

## 🔧 Advanced Usage

### Multiple Chat Support
Each search can send notifications to different Telegram chats - perfect for:
- Personal vs. business monitoring
- Different categories to different groups
- Family sharing

### Debug Mode
Full request logging shows exactly what's happening:
```
DEBUG - Link: https://www.vinted.hu/api/v2/catalog/items?page=1&per_page=20&order=newest_first&search_text=nike+air+max&catalog_ids=5
INFO - Found 20 items for query: nike air max
INFO - After filtering: 3 items
INFO - Sending 2 new items to chat 123456789
```

## 📋 Requirements

- **Python 3.8+**
- **aiohttp** (for async HTTP requests)
- **Telegram Bot Token**
- **Internet Connection**

No additional dependencies, no complex setup, no proxies needed!

## 🌟 Why Choose This Bot?

✅ **Simple Setup** - Get started in under 2 minutes  
✅ **No Proxies** - Runs reliably without complex proxy setups  
✅ **Fast Performance** - Optimized for speed and efficiency  
✅ **Rich Notifications** - Beautiful Telegram messages with all item details  
✅ **Multi-Country** - Works with any Vinted marketplace  
✅ **Duplicate-Free** - Never get the same notification twice  
✅ **Open Source** - Fully transparent and customizable  

## 🤝 Contributing

Contributions are welcome! Feel free to:
- Report bugs
- Suggest features
- Submit pull requests
- Improve documentation

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## ⚠️ Disclaimer

This bot is for educational and personal use only. Please respect Vinted's terms of service and use responsibly. The authors are not responsible for any misuse or violations.

## 🆘 Support

Having issues? Get help here:
- � **GitHub Issues**: Report bugs or request features via [GitHub Issues](https://github.com/noelz06/vinted-monitor-bot/issues)
- 👤 **GitHub**: Contact me directly [@noelz06](https://github.com/noelz06)
- 💬 **Discord**: Reach out on Discord **noeel_1122**

---

⭐ **Star this repo if you found it helpful!** ⭐

