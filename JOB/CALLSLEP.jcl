//CALLSLEP  JOB CLASS=2,MSGCLASS=X,MSGLEVEL=(1,1),TIME=(12,10),
//        COND=(12,LE),NOTIFY=&SYSUID
//****************************************************************
//* "HOLD" statement is mandatory for keep the log on FTP server.
//* It can be marked out if executed on mainframe directly.
//HOLD     OUTPUT JESDS=ALL,DEFAULT=Y,OUTDISP=(HOLD,HOLD)
//****************************************************************
//STEP1    EXEC PGM=IKJEFT01
//* The REXX program "REXSLEEP" is in PDS "&SYSUID..REXX".
//SYSEXEC  DD DSN=&SYSUID..REXX,DISP=SHR
//SYSTSPRT DD SYSOUT=*
//SYSTSIN  DD *
REXSLEEP
//****************************************************************
