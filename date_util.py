import datetime
from datetime import datetime

def removeOverlapping(timeIntervals):
    timeIntervals = sorted(timeIntervals, key=lambda tup: tup[0])
    #print('sorted intervals: ' + str(timeIntervals))
    output = []
    previous = None
    for current in timeIntervals:
        if previous is None:
            output.append(current)
            previous = current
        else:
            if current[0] <= previous[1]: # intersection
                previous[1] = max(previous[1], current[1])
            else:
                output.append(current)
                previous = current
    return output

def test():
    eventA_start = datetime.strptime('Nov 7 2015  8:32AM', '%b %d %Y %I:%M%p')
    eventA_end = datetime.strptime('Nov 7 2015  8:38AM', '%b %d %Y %I:%M%p')
    eventA = [eventA_start, eventA_end]

    eventB_start = datetime.strptime('Nov 7 2015  8:35AM', '%b %d %Y %I:%M%p')
    eventB_end = datetime.strptime('Nov 7 2015  8:43AM', '%b %d %Y %I:%M%p')
    eventB = [eventB_start, eventB_end]

    eventC_start = datetime.strptime('Nov 7 2015  9:35AM', '%b %d %Y %I:%M%p')
    eventC_end = datetime.strptime('Nov 7 2015  9:43AM', '%b %d %Y %I:%M%p')
    eventC = [eventC_start, eventC_end]

    eventD_start = datetime.strptime('Nov 7 2015  6:35AM', '%b %d %Y %I:%M%p')
    eventD_end = datetime.strptime('Nov 7 2015  6:43AM', '%b %d %Y %I:%M%p')
    eventD = [eventD_start, eventD_end]

    eventE_start = datetime.strptime('Nov 7 2015  9:38AM', '%b %d %Y %I:%M%p')
    eventE_end = datetime.strptime('Nov 7 2015  9:40AM', '%b %d %Y %I:%M%p')
    eventE = [eventE_start, eventE_end]


    events = [eventA, eventB, eventC, eventD, eventE]

    print(removeOverlapping(events))