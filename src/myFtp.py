#!/usr/bin/python

import ftplib   
import pprint
import re
import time


class myFtp(object):   
#  Message format is:  220-......  <-- this line means the message is followed by the next line.
#                      220 ......  <-- this line means the message is complete. Usually, only this line.
  re_msg=re.compile('^(?P<num>\d+)[ -](?P<info>.+)')
  re_job=re.compile('^It is known to JES as JOB(?P<jobid>\d+)$')
  dbg_banner=">>>> Debug Info: "
  fail_banner="!!!! Err: "

  def __init__(self, host, port='21',dbg_lvl=0):  
      self.__ftp=ftplib.FTP()   
      
      # debug setting
      self.__dbg_me = False
      if (0 < dbg_lvl):
         self.__dbg_me = True
      if (1 < dbg_lvl):
         self.__ftp.set_debuglevel(dbg_lvl)

      self.__jobid = 0

      self.__msg_code=0    # 220/250/...
      self.__msg_info=[]

      self.__reply_info=[] # While executing "LIST/RETR", some file info returns back.

      self.reset_reply_msg()
      self.__ftp.set_pasv(True) 
      self.__ftp.connect( host, port )   
      self.__userid = ""

  def login(self, user, passwd ):   
      self.__userid = user
      self.__ftp.login( user, passwd )   
      print self.__ftp.welcome  

  def close( self):   
      self.__ftp.quit()

  def set_pasv(self):
      self.__ftp.makepasv()

  def reset_reply_msg(self):
      del self.__reply_info[:]
      del self.__msg_info[:]
      self.__msg_code=0

  def save_reply(self, reply):
      self.__reply_info.append(reply)

  def show_reply(self):
      if self.__dbg_me:
         print myFtp.dbg_banner, "The reply info is:"
         pprint.pprint(self.__reply_info)

  def sendcmd(self, cmd):
      self.reset_reply_msg()
      self.parse_msg(self.__ftp.sendcmd(cmd))

  def del_job_log(self):
      # delete the job log from mainframe.
      try:
        self.parse_msg(self.__ftp.delete('JOB' + str(self.__jobid)))
      except ftplib.error_perm, reply:
        self.parse_msg(str(reply))
        print myFtp.fail_banner, " when delete job log:"
        print str(self.__msg_code), str(self.__msg_info)


  def get_job_log(self,fp):
      # send cmd 'RETR JOBxxxxx' and then save the job log to file 'fp'.
      # job log is also stored to self.__reply_info[].
      self.reset_reply_msg()
      try:
        self.parse_msg(self.__ftp.retrlines('RETR JOB' + str(self.__jobid), self.save_reply))
        self.show_reply()
        fp.write('\n'.join(self.__reply_info))      
      except ftplib.error_perm, reply:
        self.parse_msg(str(reply))
        print myFtp.fail_banner, " when get job log:"
        print str(self.__msg_code), str(self.__msg_info)

  def query_job_status(self):
      # return (bool01, bool02)
      # bool01: True - The jobid exist; False - The job id does NOT exist.
      # bool02: True - The job status is OUTPUT (complete); False - The job is NOT complete
      self.reset_reply_msg()
      try:
        self.parse_msg(self.__ftp.retrlines('LIST ', self.save_reply))
        self.show_reply()
        # The reply info usually contains the following info:
        # JOBNAME  JOBID    OWNER    STATUS CLASS
        # xxxxxxxx JOB11652 UserID   OUTPUT 2        (JCL error) 4 spool files
        # xxxxxxxx JOB04426 UserID   OUTPUT 2        RC=0000 4 spool file
        # xxxxxxxx JOB04423 UserID   ACTIVE 2 
        l_list=['^........ JOB', str(self.__jobid), ' +', str(self.__userid), ' +(?P<status>\w+) +.*$']
        l_re_job_status=re.compile(''.join(l_list),re.I)
        
        # Needs to get the line with JOBID and then get its status "OUTPUT|ACTIVE|..."
        for l_eachline in self.__reply_info[1:]:
            # no needs to check the first line
            l_match = l_re_job_status.match(l_eachline)
            if l_match:
               l_dict=l_match.groupdict()
               if self.__dbg_me:
                 print myFtp.dbg_banner, "JOB" + self.__jobid + " status:", l_dict["status"]
               if ('OUTPUT' == l_dict["status"]):
                 return (True, True)
               else:
                 return (True, False)
        else:
            # no line match the pattern, the job id does NOT exist.
            return (False, False)
      except ftplib.error_perm, reply:
        self.parse_msg(str(reply))
        return (False, False)


  def parse_msg(self, message):
      # parse message to __msg_code and __msg_info
      l_msg_lines=message.split('\n')
      if self.__dbg_me: 
         print myFtp.dbg_banner, "Received message is: "
         pprint.pprint(l_msg_lines)
      for l_msg_eachline in l_msg_lines:
         l_msg_match = self.re_msg.match(l_msg_eachline)
         try:
            l_msg_dict=l_msg_match.groupdict()
            ##for k,v in msg_dict.items():
            ##    print k + " --> " + v
            self.__msg_code, l_msg_info = (l_msg_dict["num"], l_msg_dict["info"])
            self.__msg_info.append(l_msg_info)
            ## msg_code is not checked here,
            ## assume the msg_code is always the same for one complete msg.
            if self.__dbg_me: 
               print myFtp.dbg_banner, "Parsing received message: "
               print self.__msg_code, str(self.__msg_info)
         except AttributeError:
            print myFtp.fail_banner, "Fail to parse the message: "
            print message
            self.__msg_code, self.__msg_info = ('----', ['----'])
            break


  def submit_job(self,cmd,fp):
      self.reset_reply_msg()
      self.parse_msg(self.__ftp.storlines(cmd, fp, self.save_reply))
      ## get the job id
      self.__jobid = 0
      for l_eachline in self.__msg_info:
          l_match=self.re_job.match(l_eachline)
          if l_match:
             try:
               l_dict=l_match.groupdict()
               self.__jobid = l_dict["jobid"]
               if self.__dbg_me:
                  print myFtp.dbg_banner, "The jobid is: ", self.__jobid, "."
             except AttributeError:
               print myFtp.fail_banner, "Fail to parse the jobid:"
               pprint.pprint(self.__msg_info)
             break 
      self.show_reply()


def test():
      print "============== start ==============="
      # debug_level:
      #   =0: no debug info
      #   =1: only the debug info from class 'myFtp', while no debug info from class 'ftplib'
      #   >1: 'myFtp" always output debug info; the debug_level is set to 'ftplib'
      debug_level=3
      ftp=myFtp(host='tom.t.o.m.com', dbg_lvl=debug_level)  
      
      print "============== start login       ==============="
      ftp.login('USERID','PASSWD')  
      
      print "============== prepare to submit ==============="
      ftp.sendcmd('SITE FILETYPE=JES')
      
      print "============== submit a job      ==============="
      filep=open('CALLSLEP.jcl','rb')
      ftp.submit_job('STOR CALLSLEP.jcl',filep)
      filep.close()
      
      print "============== set query job     ==============="
      ftp.sendcmd('site JESJOBNAME=*')
      
      print "============== query job status  ==============="
      # 5 seconds for each loop
      loopCount, sleepTime, job_exist, job_done = (10, 5, True, False)
      for i in range(0, loopCount):
         (job_exist, job_done) = ftp.query_job_status()
         if not job_exist:
            print '>>>> The job does NOT exist, please set debug level greater than 3 and chech what\'s up!'
            return
         if job_done : break
         time.sleep(sleepTime)
      else:
         # job is not completed yet
         print '>>>> The job execution needs more time, please enlagre the loopCount or sleepTime, and then try again!'
         return
    
      
      print "============== get job log       ==============="
      # The job log is wrote to file "JOBLOG.txt" in the current path.
      filep=open('JOBLOG.txt','wb')
      ftp.get_job_log(filep)
      filep.close()
     
      print "============== delete job log    ==============="
      # Without doing this, the job log is kept on mainframe,
      # then the job log will be there in the job list when you run this again,
      # but it does NOT affect the result.
      # To check that, please mark out the following "del_job_log" and set debug level larger than 1,
      # and then execute this at least 2 times.
      ftp.del_job_log() 

      print "============== close ftp session ==============="
      ftp.close()  
      print "Done."  


if __name__ == '__main__':
   test()
