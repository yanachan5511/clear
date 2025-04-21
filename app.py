from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage, FileSendMessage
import os
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

app = Flask(__name__)

# 環境変数からLINEのチャネル情報を読み込む
LINE_CHANNEL_ACCESS_TOKEN = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
LINE_CHANNEL_SECRET = os.getenv('LINE_CHANNEL_SECRET')

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

@app.route("/webhook", methods=['POST'])
def webhook():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'

# 見積内容を解析する関数
def parse_quote(text):
    lines = text.strip().split("\n")
    subject = ""
    expiry = ""
    items = []

    for line in lines:
        line = line.replace("、", ",")  # 「、」をカンマに変換

        if line.startswith("件名,"):  # 「件名、」に対応
            subject = line.split("件名,")[1].strip()
        elif line.startswith("有効期限,"):  # 「有効期限、」に対応
            expiry = line.split("有効期限,")[1].strip()
        elif "," in line:
            parts = [p.strip() for p in line.split(",")]
            if len(parts) == 4:
                name, qty, unit, price = parts
                amount = int(qty) * int(price)
                items.append({
                    "name": name,
                    "qty": qty,
                    "unit": unit,
                    "price": int(price),
                    "amount": amount
                })

    return subject, expiry, items

# PDFを作成する関数
def create_pdf(subject, expiry, items, filename):
    c = canvas.Canvas(filename, pagesize=A4)
    width, height = A4

    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, height - 50, f"見積書：{subject}")
    c.setFont("Helvetica", 10)
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

            # 保存先パス
            folder = "static/pdfs"
            os.makedirs(folder, exist_ok=True)
            filename = os.path.join(folder, f"{subject}.pdf")

            # PDF 作成
            create_pdf(subject, expiry, items, filename)

            # 公開URL作成
            pdf_url = f"https://clear-75vj.onrender.com/static/pdfs/{subject}.pdf"

            # LINEに送信
            line_bot_api.push_message(
                event.source.user_id,
                FileSendMessage(
                    original_content_url=pdf_url,
                    file_name=f"{subject}.pdf"
                )
            )

            reply_text = f"見積書（{subject}）のPDFを作成し、送信しました！"

        except Exception as e:
            reply_text = f"エラーが発生しました: {str(e)}"

    else:
        reply_text = "メッセージを受け取りました！"

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply_text)
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
