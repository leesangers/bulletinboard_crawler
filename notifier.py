import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

class EmailNotifier:
    def __init__(self, smtp_server="smtp.gmail.com", port=587):
        self.smtp_server = smtp_server
        self.port = port
        self.email_user = os.getenv("EMAIL_USER")
        self.email_pw = os.getenv("EMAIL_APP_PASSWORD")
        self.recipient_email = os.getenv("RECIPIENT_EMAIL")

    def send_notification(self, kofair_posts, mss_posts, kofair_error=False, mss_error=False):
        """
        Sends an email notification with the list of new posts, split by source.
        Always sends even if no new posts are found.
        Supports multiple recipients via comma-separated RECIPIENT_EMAIL.
        """
        if not self.email_user or not self.email_pw or not self.recipient_email:
            print("Email credentials or recipient not configured in environment variables.")
            return False

        # Handle multiple recipients
        recipients = [r.strip() for r in self.recipient_email.split(",") if r.strip()]

        try:
            msg = MIMEMultipart()
            msg["From"] = self.email_user
            msg["To"] = ", ".join(recipients)
            
            total_count = len(kofair_posts) + len(mss_posts)
            if total_count > 0:
                msg["Subject"] = f"[게시판 알림] 신규 게시물 ({total_count}건)"
            else:
                msg["Subject"] = f"[게시판 알림] 신규 게시글 없음"

            html = "<h2>게시판 신규 등록 게시물 알림</h2>"
            
            def generate_table_html(title, posts, is_error=False):
                section_html = f"<h3>[{title}]</h3>"
                if is_error:
                    section_html += "<p style='color: #d93025; font-weight: bold;'>⚠️ 해당 게시판 정보를 가져오는 중 오류가 발생했습니다.</p><br/>"
                    return section_html
                
                if not posts:
                    section_html += "<p style='color: #70757a;'>새 게시글이 없습니다.</p><br/>"
                    return section_html
                
                section_html += "<table border='1' cellpadding='5' style='border-collapse: collapse; width: 100%;'>"
                section_html += "<thead><tr style='background-color: #f2f2f2;'><th>번호</th><th>제목</th><th>등록일</th></tr></thead>"
                section_html += "<tbody>"
                for post in posts:
                    link_style = "color: #1a73e8; text-decoration: none; font-weight: bold;"
                    section_html += f"<tr><td>{post['id']}</td><td><a href='{post['url']}' style='{link_style}'>{post['title']}</a></td><td>{post['date']}</td></tr>"
                section_html += "</tbody></table><br/>"
                return section_html

            # KOFAIR first, then MSS
            html += generate_table_html("KOFAIR - 한국공정거래조정원", kofair_posts, kofair_error)
            html += generate_table_html("MSS - 중소벤처기업부", mss_posts, mss_error)
            
            html += "<p style='color: grey;'>본 메일은 자동 발송되었습니다.</p>"

            msg.attach(MIMEText(html, "html"))

            with smtplib.SMTP(self.smtp_server, self.port) as server:
                server.starttls()
                server.login(self.email_user, self.email_pw)
                # Ensure we send to all recipients explicitly
                server.sendmail(self.email_user, recipients, msg.as_string())
            
            print(f"Successfully sent notification to {len(recipients)} recipients: {', '.join(recipients)}")
            print(f"Total posts notified: {total_count} (KOFAIR: {len(kofair_posts)}, MSS: {len(mss_posts)})")
            return True
        except Exception as e:
            print(f"FAILED to send email: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == "__main__":
    # Test block
    test_posts = [
        {"id": "test1", "source": "KOFAIR", "title": "Test Title 1", "date": "2024-03-17", "url": "https://example.com/1"},
        {"id": "test2", "source": "MSS", "title": "Test Title 2", "date": "2024-03-17", "url": "https://example.com/2"}
    ]
    # Set dummy env vars for local test if needed (DO NOT COMMIT SECRETS)
    notifier = EmailNotifier()
    notifier.send_notification(test_posts, [])
