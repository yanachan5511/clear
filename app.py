from flask import Flask, request
from linebot import LineBotApi, WebhookHandler
from linebot.models import MessageEvent, TextMessage
from linebot.exceptions import InvalidSignatureError  # 追加
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
import os

# Flask アプリケーションを作成
app = Flask(__name__)

# LINE BotのAPIとハンドラーを初期化
line_bot_api = LineBotApi('YOUR_CHANNEL_ACCESS_TOKEN')
handler = WebhookHandler('YOUR_CHANNEL_SECRET')

# 日本語フォントを登録
pdfmetrics.registerFont(TTFont('IPAexGothic', 'static/fonts/ipaexg.ttf'))

def create_pdf(subject, expiry, items, filename):
    c = canvas.Canvas(filename, pagesize=A4)
    width, height = A4

    # フォント設定（日本語フォントを指定）
    c.setFont("IPAexGothic", 14)

    c.drawString(50, height - 50, f"見積書：{subject}")
    c.setFont("IPAexGothic", 10)
    c.drawString(50, height - 70, f"有効期限：{expiry}")

    c.drawString(50, height - 100, "項目明細：")
    y = height - 120
    total = 0

    for item in items:
        line = f"{item['name']}　{item['qty']} {item['unit']} x ¥{item['price']} = ¥{item['amount']}"
        c.drawString(60, y, line)
        y -= 20
        total += item['amount']

    c.drawString(50, y - 10, f"合計金額：¥{total}")
    c.save()

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    msg = event.message.text

    if "件名" in msg and "有効期限" in msg:
        try:
            subject, expiry, items = parse_quote(msg)
            folder = "static/pdfs"
            os.makedirs(folder, exist_ok=True)
            filename = os.path.join(folder, f"{subject}.pdf")
            create_pdf(subject, expiry, items, filename)

            pdf_url = f"https://clear-75vj.onrender.com/static/pdfs/{subject}.pdf"
            reply_text = f"見積書（{subject}）のPDFを作成しました！\nこちらからダウンロードできます：\n{pdf_url}"

        except Exception as e:
            reply_text = f"エラーが発生しました: {str(e)}"
    else:
        reply_text = "メッセージを受け取りました！（件名・有効期限の情報が必要です）"

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply_text)
    )

@app.route("/webhook", methods=["POST"])
def webhook():
    signature = request.headers["X-Line-Signature"]
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        print("Invalid signature. Please check your channel access token and secret.")
        return 'Invalid signature', 400
    except Exception as e:
        print(f"Error: {e}")
        return 'Internal Server Error', 500

    return 'OK', 200

# アプリケーションを実行
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
