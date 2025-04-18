from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

import os
from fpdf import FPDF
import datetime

def generate_pdf_from_structured_text(text):
    # 初期化
    subject = ""
    expiry = ""
    total = ""
    items = []

    lines = text.splitlines()
    parsing_items = False

    for line in lines:
        line = line.strip()

        # 全角カンマを半角に置き換える
        line = line.replace("、", ",")

        if line.startswith("件名:"):
            subject = line.replace("件名:", "").strip()
        elif line.startswith("有効期限:"):
            expiry = line.replace("有効期限:", "").strip()
        elif line.startswith("お見積金額:"):
            total = line.replace("お見積金額:", "").strip()
        elif line.startswith("明細:"):
            parsing_items = True
        elif parsing_items and line:
            parts = line.split(",")
            if len(parts) == 5:
                items.append(parts)

    # PDF作成
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(200, 10, txt="見積書", ln=True, align='C')

    # 件名・日付など
    pdf.set_font("Arial", size=12)
    today = datetime.date.today().strftime("%Y年%m月%d日")

    pdf.cell(200, 10, txt=f"作成日: {today}", ln=True, align='R')
    pdf.ln(5)
    pdf.cell(200, 10, txt=f"件名: {subject}", ln=True)
    pdf.cell(200, 10, txt=f"有効期限: {expiry}", ln=True)
    pdf.cell(200, 10, txt=f"お見積金額: ¥{total}", ln=True)
    pdf.ln(10)

    # 明細表ヘッダー
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(60, 10, "摘要", border=1)
    pdf.cell(20, 10, "数量", border=1)
    pdf.cell(20, 10, "単位", border=1)
    pdf.cell(30, 10, "単価", border=1)
    pdf.cell(30, 10, "金額", border=1)
    pdf.ln()

    # 明細内容
    pdf.set_font("Arial", size=12)
    for item in items:
        pdf.cell(60, 10, item[0], border=1)
        pdf.cell(20, 10, item[1], border=1)
        pdf.cell(20, 10, item[2], border=1)
        pdf.cell(30, 10, item[3], border=1)
        pdf.cell(30, 10, item[4], border=1)
        pdf.ln()

    # 保存
    filename = f"/tmp/estimate_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
    pdf.output(filename)

    return filename

app = Flask(__name__)

# 環境変数から読み込む（Renderに登録する）
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

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    msg = event.message.text

    if "件名:" in msg and "明細:" in msg:
        # PDFを作成
        pdf_path = generate_pdf_from_structured_text(msg)

        # PDF作成完了のメッセージを送信
        reply_text = "見積書PDFを作成しました！"
        
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=reply_text)
        )
    else:
        # 何もしない（返信なし）
        return

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
