import csv
import random
import math
import operator

# prepare data
dataFile = 'previousGames.csv'
usersInput = []
enemyHistory = []
playerHistory = []
finished = False
trainingSet=[]
turnNumber = 0

def loadDataset(filename,trainingSet=[]):
    ##Sets up a csv file to be able to be processec.
    with open(filename, 'rb') as csvfile:
        lines = csv.reader(csvfile)
        dataset = list(lines)
        for x in range(len(dataset)):
            for y in range(20):
                dataset[x][y] = int(dataset[x][y])
                trainingSet.append(dataset[x])
 
 
def euclideanDistance(instance1, instance2, length):
    #This gets the distance between the input and each of the available pieces of data.
    distance = 0
    for x in range(length):
        distance += pow((int(instance1[x]) - int(instance2[x])), 2)
    return math.sqrt(distance)
 
def getNeighbors(trainingSet, usersInput, k):
    #This iterates through the set of available data and identifies the three closest nieghbours to the input.
    distances = []
    length = len(usersInput)
    for x in trainingSet:
        dist = euclideanDistance(usersInput, x, length)
        distances.append((x, dist))
    distances.sort(key=operator.itemgetter(1))
    neighbors = []
    for x in range(k):
        neighbors.append(distances[x][0])
    return neighbors
 
def getResponse(neighbors):
    #Takes the three closest neighbours and decides using them which category it fits into 
    classVotes = {}
    for x in range(len(neighbors)):
        response = neighbors[x][-1]
        if response in classVotes:
            classVotes[response] += 1
        else:
            classVotes[response] = 1
    sortedVotes = sorted(classVotes.iteritems(), key=operator.itemgetter(1), reverse=True)
    return sortedVotes[0][0]
    
def generatePrediction(trainingSet, usersInput):
    # generate predictions
    k = 3
    neighbors = getNeighbors(trainingSet, usersInput, k)
    result = getResponse(neighbors)
    print('>predicted game type = ' + repr(result))
    return result

#tit for tat
def predictTitForTat():
    return playerHistory[playerHistory.length - 1];

#unforgiving
def predictUnforgiving():
    for choice in playerHistory:
        if choice:
            return True
    return False

#champion
def predictChampion():
    if turnNumber < 6:
        return False
    elif turnNumber < 11:
        return playerHistory[playerHistory.length - 1]

    points = 0;

    for i in range(0, 11):
        if playerHistory[i]: 
            points += 1

    if playerHistory[playerHistory.length - 1] or points > 5:
        return playerHistory[playerHistory.length - 1]

    return True


#handshake
def predictHandshake():
    if turnNumber == 1:
        return True
    elif turnNumber == 2:
        return False
    elif turnNumber == 3:
        return True

    for i in range(0, 3):
        if(not (playerHistory[i] and enemyHistory[i])):
            return True;
    return False;
    
#Ressurection
def predictResurrection():
    if turnNumber <= 5:
        return False

    for i in range(turnNumber - 5, turnNumber):
        if not playerHistory[i]:
            return playerHistory[playerHistory.length - 1];

    return True

#Grumpy
def predictGrumpy():
    happiness = 7

    if(playerHistory[playerHistory.length - 1]):
        happiness -= 1
    else:
        happiness += 1
    
    return happiness < 6

def doPredictions(enemyStrategy):
    result = True

    if enemyStrategy == "Grumpy":
        result = predictGrumpy()
    elif enemyStrategy == "Resurrection":
        result = predictResurrection()
    elif enemyStrategy == "Handshake":
        result = predictHandshake()
    elif enemyStrategy == "Champion":
        result = predictChampion()
    elif enemyStrategy == "TFT":
        result = predictTitForTat()
    elif enemyStrategy == "Grudger":
        result = predictUnforgiving()
    if result == False:
    	print("Opponents next move (prediction) - silence")
    elif result == True:
    	print("Opponents next move (prediction) - betray")

loadDataset(dataFile , trainingSet)
print('Train set: ' + repr(len(trainingSet)))

while finished == False:
    turnNumber += 1
    userGo = input("Input your last move - ")
    usersInput.append(userGo)
    playerHistory.append(userGo)
    enemyGo = input("Input the opponents last move - ")
    usersInput.append(enemyGo)
    playerHistory.append(enemyGo)

    result = generatePrediction(trainingSet, usersInput)
    (playerStrategy, enemyStrategy) = result.split("-")
    print('>predicted enemy strategy = ' + enemyStrategy)
    print('>predicted player strategy = ' + playerStrategy)

    doPredictions(enemyStrategy)
