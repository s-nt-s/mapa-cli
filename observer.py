from smtplib import SMTP
from email.message import EmailMessage
from os.path import basename
from core.filemanager import CNF
from core.tunnel import SSHTunnel, HostPort
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from os.path import expanduser, isdir, realpath
import logging

logger = logging.getLogger(__name__)


DIRS = tuple(sorted(
    filter(isdir, set(map(
        lambda x: realpath(expanduser(x)),
        (CNF.nominas, CNF.expediente, CNF.retribuciones, CNF.informe_horas)
    )))
))

def send_email(filepath: str):
    logger.info(f"send_email({filepath})")
    filename = basename(filepath)
    msg = EmailMessage()
    msg["From"] = CNF.smtp.user
    msg["To"] = CNF.smtp.default_to
    msg["Subject"] = f"[MAPA-CLI] {filename}"

    with open(filepath, "rb") as f:
        data = f.read()
    msg.add_attachment(
        data,
        maintype="application",
        subtype="octet-stream",
        filename=filename
    )

    with SMTP(CNF.smtp.host, CNF.smtp.port) as server:
        server.starttls()
        server.login(CNF.smtp.user, CNF.smtp.pasw)
        server.send_message(msg)


class NewFileHandler(FileSystemEventHandler):
    def on_created(self, event):
        if not event.is_directory:
            send_email(event.src_path)

def main():
    handler = NewFileHandler()
    observer = Observer()
    for d in DIRS:
        logger.info(f"Observando {d}")
        observer.schedule(handler, d, recursive=False)
    
    observer.start() 
    try:
        observer.join()
    except KeyboardInterrupt:
        observer.stop()
        observer.join()

if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format='%(levelname)-8s %(message)s')
    if len(sys.argv) > 1:
        send_email(sys.argv[1])
        sys.exit()
    main()
