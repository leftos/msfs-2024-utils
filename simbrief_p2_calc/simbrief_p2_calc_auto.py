""" Figure out max number of passengers and freight for a given simbrief plan """

# pylint: disable=line-too-long

import argparse
import math
import requests

known_airframes = {
    "Fenix A320 IAE": { 
        "id": "a320iae", 
        "max_pax": 170, 
    }
}

# Read arguments
# pax
# cargo
# estimated_takeoff_weight
parser = argparse.ArgumentParser()
parser.add_argument("--username", type=str)
parser.add_argument("--airframe", type=str)
parser.add_argument("--desired_pax", type=int, default=None)
parser.add_argument("--desired_freight", type=int, default=None)
args = parser.parse_args()

if args.desired_pax is not None and args.desired_freight is not None:
    raise ValueError("You can't specify both desired_pax and desired_freight")

# Get airframe data
# Find the airframe in the known_airframes dictionary via the airframe argument, either as the dictionary key or the "id" value
airframe = known_airframes.get(args.airframe) or next((airframe for airframe in known_airframes.values() if airframe["id"] == args.airframe), None)
if airframe is None:
    raise ValueError(f"Unknown airframe: {args.airframe}")
max_pax = airframe["max_pax"]

# get the latest simbrief ofp json
simbrief_ofp_url = f"https://www.simbrief.com/api/xml.fetcher.php?username={args.username}&json=1"
response = requests.get(simbrief_ofp_url)
response.raise_for_status()
simbrief_ofp = response.json()

print("=================================================")
print("Simbrief OFP Info")
print("=================================================")
max_takeoff_weight = float(simbrief_ofp["weights"]["max_tow"])
print(f"Max takeoff weight: {int(max_takeoff_weight)}")
etow = float(simbrief_ofp["weights"]["est_tow"])
print(f"Estimated takeoff weight: {int(etow)}")
remaining_takeoff_weight = max_takeoff_weight - etow
print(f"Remaining takeoff weight: {int(remaining_takeoff_weight)}")
cargo_per_pax = float(simbrief_ofp["weights"]["bag_weight"])
print(f"Cargo per pax: {cargo_per_pax}")
person_weight_per_pax = float(simbrief_ofp["weights"]["pax_weight"])
print(f"Person weight per pax: {person_weight_per_pax}")
total_zfw_per_pax = person_weight_per_pax + cargo_per_pax

pax = int(simbrief_ofp["weights"]["pax_count_actual"])
print(f"Actual pax: {pax}")
bags = int(simbrief_ofp["weights"]["bag_count_actual"])
print(f"Actual bags: {bags}")
freight = int(simbrief_ofp["weights"]["freight_added"])
print(f"Freight: {freight}")
extra_cargo = float(simbrief_ofp["weights"]["cargo"]) - freight - bags * cargo_per_pax
print(f"Extra cargo: {math.ceil(extra_cargo)}")

print("=================================================")
print("Calculations")
print("=================================================")
# We want every passenger to be able to bring a checked bag
if bags < pax:
    print("Adjusting passengers so that everyone can bring a checked bag")
    removed_passengers = pax - bags
    print(f"Removing {removed_passengers} passengers")
    pax -= removed_passengers
    print(f"New pax: {pax}")
    etow -= removed_passengers * person_weight_per_pax
    remaining_takeoff_weight = max_takeoff_weight - etow
    print(f"Remaining takeoff weight: {int(remaining_takeoff_weight)}")
    print("=================================================")

if args.desired_freight is None:
    final_freight = float(freight)
    if remaining_takeoff_weight != 0:
        additional_freight = remaining_takeoff_weight
        print(f"Remaining takeoff weight added to freight: {int(additional_freight)}")
        final_freight = freight + additional_freight
        print(f"New freight: {int(final_freight)}")
        print("=================================================")
    # How many additional passengers with baggage could we add?
    additional_pax = int(min(remaining_takeoff_weight // total_zfw_per_pax, max_pax - pax))
    if additional_pax != 0:
        print(f"There's room for {additional_pax} extra passengers with baggage")

        final_pax = pax + additional_pax
        print(f"New pax: {final_pax}")
        
        # Assuming we take on the maximum number of additional passengers, do we still have room for freight?
        remaining_takeoff_weight -= additional_pax * total_zfw_per_pax
        additional_freight = remaining_takeoff_weight
        final_freight = freight + additional_freight
        print(f"New freight: {int(final_freight)}")
        print("=================================================")

    # SimBrief likes to mess around with the average passenger weight instead of using a consistent average weight per passenger,
    # so our calculation might result in fewer passengers than the already valid simbrief flight plan
    if final_freight < 0 and additional_pax <= 0:
        final_pax = pax
        final_freight = 0

    # if max_freight is negative, we need to adjust the number of passengers until the freight is at least 0    
    if final_freight < 0:
        print(f"Removing passengers because we're overweight")
        removed_passengers = math.ceil(-final_freight / total_zfw_per_pax)
        print(f"Removing {removed_passengers} passengers")
        final_pax -= removed_passengers
        final_freight += removed_passengers * total_zfw_per_pax
        print("=================================================")

    if args.desired_pax is not None:
        print(f"New pax: {final_pax}")
        desired_pax = int(args.desired_pax)
        print(f"Desired pax: {desired_pax}")
        extra_pax = desired_pax - final_pax
        print(f"Extra pax: {extra_pax}")
        final_pax += extra_pax
        final_freight -= extra_pax * total_zfw_per_pax
        print(f"New freight: {int(final_freight)}")
        print("=================================================")

        # if max_freight is negative, we need to adjust the number of passengers until the freight is at least 0
        if final_freight < 0:
            print(f"Removing passengers because we're overweight")
            removed_passengers = math.ceil(-final_freight / total_zfw_per_pax)
            print(f"Removing {removed_passengers} passengers")
            final_pax -= removed_passengers
            final_freight += removed_passengers * total_zfw_per_pax
            print("=================================================")
else:
    desired_freight = int(args.desired_freight)
    print(f"Desired freight: {desired_freight}")
    extra_freight = desired_freight - freight
    print(f"Extra freight: {extra_freight}")
    remaining_takeoff_weight -= extra_freight
    print(f"Remaining takeoff weight: {int(remaining_takeoff_weight)}")
    additional_pax = int(min(remaining_takeoff_weight // total_zfw_per_pax, max_pax - pax))
    print(f"There's room for {additional_pax} extra passengers with baggage")
    remaining_takeoff_weight -= additional_pax * total_zfw_per_pax
    final_pax = pax + additional_pax
    final_freight = freight + extra_freight + remaining_takeoff_weight
    print("=================================================")

print(f"Final pax: {int(final_pax)}")
print(f"Final max freight: {int(final_freight)}")