import subprocess
from apscheduler.schedulers.blocking import BlockingScheduler

def exec_interval():
    print("Starting update ...")
    result = subprocess.run(["pip", "install", "-U", "youtube-dl"])
    print("done:", result)

sched = BlockingScheduler()
sched.add_job(exec_interval, 'interval', seconds=60*60)

sched.start()
