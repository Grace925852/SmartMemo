import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.config import settings

def send_email_sync(to_email: str, subject: str, body: str):
    """
    Fonction synchrone pour envoyer un email. Sera exécutée dans un BackgroundTask.
    """
    # Si les paramètres SMTP ne sont pas configurés, on simule l'envoi
    if not all([settings.SMTP_SERVER, settings.SMTP_PORT, settings.SMTP_USERNAME, settings.SMTP_PASSWORD]):
        print(f"\n[{'='*50}]")
        print(f"SIMULATION EMAIL à : {to_email}")
        print(f"Sujet : {subject}")
        print(f"Message : \n{body}")
        print(f"[{'='*50}]\n")
        return

    msg = MIMEMultipart()
    msg['From'] = settings.SMTP_FROM_EMAIL or settings.SMTP_USERNAME
    msg['To'] = to_email
    msg['Subject'] = subject

    msg.attach(MIMEText(body, 'html'))

    try:
        server = smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT)
        server.starttls()
        server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()
        print(f"Email envoyé avec succès à {to_email}")
    except Exception as e:
        print(f"Erreur lors de l'envoi de l'email à {to_email}: {e}")

def send_otp_email(to_email: str, otp_code: str):
    subject = "Votre code de réinitialisation de mot de passe"
    body = f"""
    <html>
        <body>
            <h2>Réinitialisation de mot de passe SmartMemo</h2>
            <p>Bonjour,</p>
            <p>Vous avez demandé à réinitialiser votre mot de passe.</p>
            <p>Voici votre code de sécurité (valide 15 minutes) :</p>
            <h1 style="color: #4CAF50;">{otp_code}</h1>
            <p>Si vous n'êtes pas à l'origine de cette demande, vous pouvez ignorer cet email.</p>
        </body>
    </html>
    """
    send_email_sync(to_email, subject, body)
