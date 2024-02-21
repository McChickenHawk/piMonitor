import sqlite3
from icmplib import ping

dbLocation = 'databases/connections.db'
#Executes any type of query and returns the results (if any)
def sqlQuery(query):
    con = sqlite3.connect(dbLocation)
    cur = con.cursor()
    while True:
        try:
            cur.execute(query)
            res = cur.fetchall()
            con.commit()
            con.close()
            return res
        except sqlite3.OperationalError:
            print("Database Locked")
            con.close()
            break

#Get a list of all nodes in the database
def importConnection():
    res = sqlQuery("SELECT * FROM connections")
    return res

class Connection:

    def __init__(self, hostname, ipAddress):
        self.hostname = hostname
        self.ipAddress = ipAddress
        self.isAlive = 0

    def showConnectionInfo(self):
        return self.hostname, self.ipAddress

    def increaseFailures(self):
        failures = sqlQuery(f"SELECT failuresSinceLastSuccessfulPing FROM connections WHERE hostname = '{self.hostname}'")
        #failures comes in as a list with a tuple in it that contains the data
        numberToIncrease = [tempList[0] for tempList in failures]
        #this is the best way I found to extract the data from the tuple. I don't know how to convert it to a primative int
        numberToIncrease[0] += 1
        sqlQuery(f"UPDATE connections SET failuresSinceLastSuccessfulPing = '{numberToIncrease[0]}' WHERE hostname = '{self.hostname}' ")

    def resetFailures(self):
        #on a successful ping, reset to zero
        sqlQuery(f"UPDATE connections SET failuresSinceLastSuccessfulPing = 0 WHERE hostname = '{self.hostname}' ")

    def pingHost(self):
        result = ping(self.ipAddress, count=1, interval=1, timeout=2, id=None, source=None, family=None, privileged=True)
        if (result.packets_received == 0):
            self.isAlive = 0
            self.increaseFailures()
            #Updating the Database to show that the node is currently offline
            sqlQuery(f"UPDATE connections SET isAlive = 0 WHERE ipAddress = '{self.ipAddress}'")
            #Updating the Database to reflect how the amount of failed pings since the last successful one
            failureCountQuery = sqlQuery(f"SELECT failuresSinceLastSuccessfulPing FROM connections WHERE ipAddress = '{self.ipAddress}'")
            failureCount = [templist[0] for templist in failureCountQuery]
            if failureCount[0] > 149: #If the number of failed pings in greater than 150
                adminAlertQuery = sqlQuery(f"SELECT adminAlerted FROM connections WHERE ipAddress = '{self.ipAddress}'")
                adminAlert = [templist[0] for templist in adminAlertQuery]
                #A push notification will NOT be sent if the adminAlerted field is true in the Database
                if adminAlert[0] == 0:
                    pushAlert(f"'{self.hostname}' has went offline")
                    #Updating the Database to reflect that the Admin has been notified.
                    sqlQuery(f"UPDATE connections SET adminAlerted = 1 WHERE ipAddress = '{self.ipAddress}'")
        else:
            self.isAlive = 1
            self.resetFailures()
            sqlQuery(f"UPDATE connections SET isAlive = 1 WHERE ipAddress = '{self.ipAddress}'")
            adminAlertQuery = sqlQuery(f"SELECT adminAlerted FROM connections WHERE ipAddress = '{self.ipAddress}'")
            adminAlert = [templist[0] for templist in adminAlertQuery]
            # Resetting the adminAlerted field to False if it's currently True
            if adminAlert[0] == 1:
                # Updating the Database to reflect that the Admin has been notified.
                sqlQuery(f"UPDATE connections SET adminAlerted = 0 WHERE ipAddress = '{self.ipAddress}'")


#Creates an object of each node and is stored in a single list
def monitorInit(connections):
    objects = []
    for i in connections:
        obj = Connection(i[0], i[1]) #I realize that indexing into an Array is not the best way to extract data. Reorganizing the table would mess up the script. More to come on that.
        objects.append(obj)
    return objects

def pushAlert(message):
    #Alerting the admin via the Pushover App (Apple)
    import http.client, urllib
    conn = http.client.HTTPSConnection("api.pushover.net:443")
    conn.request("POST", "/1/messages.json",
                 urllib.parse.urlencode({
                     "token": "aovbpjc96o4314a5be3x3eaupxydtg",
                     "user": "udgkhjdx6xyj9n18pjgr9s3cueu72e",
                     "message": message,
                 }), {"Content-type": "application/x-www-form-urlencoded"})
    conn.getresponse()

#Main function, everything is centralized to this point
def startMonitor():
    connections = importConnection()
    numberOfObjects = len(connections)
    connectionList = monitorInit(connections)
    while True:
        for i in connectionList:
            i.pingHost()

if __name__ == '__main__':
    startMonitor()


