import scipy.io as sio
import numpy as np
from simulatedAnnealing_Bermuda import simulatedAnnealing_Bermuda
from pymap3d import geodetic2ecef


#Load GNSS Data during the time of expedition (25 through 40.9) hours
def load_and_process_data(path):
    data = sio.loadmat(path)
    days = data['days'].flatten() - 59015
    times = data['times'].flatten()
    datetimes = (days * 24 * 3600) + times
    condition_GNSS = (datetimes/3600 >= 25) & (datetimes / 3600 <= 40.9)
    time_GNSS = datetimes[condition_GNSS]/3600
    x,y,z = data['x'].flatten()[condition_GNSS], data['y'].flatten()[condition_GNSS], data['z'].flatten()[condition_GNSS]
    return time_GNSS, x,y,z

paths = [
    '../GPSData/Unit1-camp_bis.mat',
    '../GPSData/Unit2-camp_bis.mat',
    '../GPSData/Unit3-camp_bis.mat',
    '../GPSData/Unit4-camp_bis.mat'
]

all_data = [load_and_process_data(path) for path in paths]
common_datetimes = set(all_data[0][0])
for data in all_data[1:]:
    common_datetimes.intersection_update(data[0])
common_datetimes = sorted(common_datetimes)

filtered_data = []
for datetimes, x, y, z in all_data:
    mask = np.isin(datetimes, common_datetimes)
    filtered_data.append([np.array(datetimes)[mask], np.array(x)[mask], np.array(y)[mask], np.array(z)[mask]])
filtered_data = np.array(filtered_data)

#Initialize Coordinates in form of Geiger's Method
GPS_Coordinates = np.zeros((len(filtered_data[0,0]),4,3))
for i in range(len(filtered_data[0,0])):
    for j in range(4):
        GPS_Coordinates[i,j,0] = filtered_data[j,1,i]
        GPS_Coordinates[i, j, 1] = filtered_data[j, 2, i]
        GPS_Coordinates[i, j, 2] = filtered_data[j, 3, i]

#Initialize Dog Acoustic Data
offset = 66828#68126 #Why? This is approximately overlaying them now
data_DOG = sio.loadmat('../GPSData/DOG3-camp.mat')['tags'].astype(float)
acoustic_DOG = np.unwrap(data_DOG[:,1] / 1e9*2*np.pi) / (2*np.pi) #Why?
time_DOG = (data_DOG[:, 0] + offset) / 3600
condition_DOG = (time_DOG >=25) & (time_DOG <= 40.9)
time_DOG, acoustic_DOG = time_DOG[condition_DOG], acoustic_DOG[condition_DOG]

#Get data at matching time stamps between acoustic data and GNSS data
time_GNSS = filtered_data[0,0]
valid_acoustic_DOG = np.full(time_GNSS.shape, np.nan)
valid_timestamp = np.full(time_GNSS.shape, np.nan)

common_indices = np.isin(time_GNSS, time_DOG)
time_GNSS = time_GNSS[common_indices]
GPS_Coordinates = GPS_Coordinates[common_indices]

#Find repeated timestamps and remove them
repeat = np.full(len(time_DOG), False)
for i in range(1,len(time_DOG)):
    if time_DOG[i-1] == time_DOG[i]:
        repeat[i] = True

time_DOG = time_DOG[~repeat]
acoustic_DOG = acoustic_DOG[~repeat]

common_indices2 = np.isin(time_DOG, time_GNSS)
time_DOG = time_DOG[common_indices2]
acoustic_DOG = acoustic_DOG[common_indices2]
print(len(time_DOG))
print(len(time_GNSS))
print(len(acoustic_DOG))
print(len(GPS_Coordinates))

valid_acoustic_DOG = acoustic_DOG
valid_timestamp = time_DOG

#Take every 30th coordinate (reduce computation time for testing)
valid_acoustic_DOG=valid_acoustic_DOG[0::30]
valid_timestamp=valid_timestamp[0::30]
GPS_Coordinates = GPS_Coordinates[0::30]

# initial_dog_guess = np.mean(GPS_Coordinates[:,0], axis=0)
# initial_dog_guess[2] += 5000
sound_speed = 1515
initial_dog_guess=np.array([1979509.5631926274, -5077550.411986372, 3312551.0725191827]) #Thalia's guess for CDOG3

gps1_to_others = np.array([[0,0,0],[0, -4.93, 0], [-10.2,-7.11,0],[-10.1268,0,0]])
initial_lever_guess = np.array([-6.4, 2.46, 0])
simulatedAnnealing_Bermuda(300, GPS_Coordinates, initial_dog_guess, valid_acoustic_DOG, gps1_to_others, initial_lever_guess, valid_timestamp, sound_speed)

#could potentially make faster by only taking every 5th or 10th point or so
#THERE IS A HUUUUUUUUUUGE OFFSET B/W GPS TIMESTAMPS AND THE DOG ACOUSTIC TIMESTAMPS
#Somehow need to align time stamps from DOG and GNSS

#Also fix the time plot by having GNSS correspond to its time and CDog correspond to CDOG time

#Current Goal is to parse data in the correct way so that everything is lined up perfectly.
#How to fix the bigly indexing error?
#Way of making plot is messed up bc I'm indexing on Time_Dog for both,
#Need to index on Time_GNSS for GNSS
#Need to organize so that "times" indexes correctly for both DOG and GNSS

#Indexing is still super off!