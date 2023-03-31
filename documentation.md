# Documentation for the GBAD APIs
Friday December 16, 2022

Written by Ian McKechnie


## Introduction
There are currently 5 endpoints that you can hit. They are: dataportal, GBADsTables, GBADsTable, GBADsPublicQuery, and GBADsLivestockPopulation. There is an explination for each for what they do, the required and optional fields for each, and an example of the output.

## dataportal
#### Endpoint Introduction
This is used to view the data portal, it gives more info on the APIs and example endpoints you can hit.

#### How to run
You can access this API by going to either
1. http://gbadske.org:9000/dataportal/

or if you're running it locally

2. http://localhost:9000/dataportal/

#### Output Example
```
Introduction

Welcome to the GBADs Data Portal and API. Through this portal you can retrieve any data contained in the GBADs public databases. This public data portal does not require a login or API tokens. The Portal currently contains data from OIE, FAOSTAT, and the Central Statistical Agency of Ethiopia. Other data will be added in the future. This introductory page contains information on how to use the Portal and has a Quick API Guide with common API calls that you can use and adapt.
...
```
//Note that ellipsis indicates that the rest of the page is not shown here


## GBADsTables
#### Endpoint Introduction

This API returns a list of tables in the GBADs database.  It is used by the dataportal to generate the list of tables that are available for the user to query.

#### How to run

You can access this API by going to either
1. http://gbadske.org:9000/GBADsTables/public?format=html

or if you're running it locally

2. http://localhost:9000/GBADsTables/public?format=html

#### API Parameters
**Optional Parameters**
1. format - The format of the output.  It can be either *text* or anything else which will be treated as *html*.
    - It will default to html if no format is specified

#### Output Example
```
GBADs Public Database Tables

- biomass_oie
- countries_adminunits_iso
- countries_gdi_un
- countries_geo_area
- countries_hdi_un
- countries_human_pop_un
- countries_incomegroups_worldbank
- country_info
- eth_csa_camels_category
- eth_csa_camels_dairy
- eth_csa_camels_estimation
- eth_csa_camels_health
- eth_csa_camels_holdings
```

## GBADsTable
#### Endpoint Introduction

This API returns the contents of a specific table in the GBADs database.  It is used by the dataportal to generate the list of the table column names for the user.

#### How to run
You can access this API by going to either
1. http://gbadske.org:9000/GBADsTable/public?table_name=livestock_production_faostat&format=html

or if you're running it locally

2. http://localhost:9000/GBADsTable/public?table_name=livestock_production_faostat&format=html

#### API Parameters
**Required Parameters**
1. table_name - this is the name of the table you want to query.
    1. Note, You can get a list of the tables by using the GBADsTables API from above

**Optional Parameters**
1. format - The format of the output.  It can be either *html* or anything else which will be treated as *text*.
    - It will default to html if no format is specified
#### Output Example

```
Data Fields for livestock_production_faostat

- year (integer)
- population (bigint)
- country (character varying)
- species (character varying)
- flag (character varying)
```

## GBADsPublicQuery
#### Endpoint Introduction
This API returns the contents of a specific query performed on a specific table in the GBADs database.

#### How to run
You can access this API by going to either
1. http://gbadske.org:9000/GBADsPublicQuery/livestock_production_faostat?fields=country,year,species,population&query=year=2017%20AND%20species=%27Goats%27&format=html

or if you're running it locally

2. http://localhost:9000/GBADsPublicQuery/livestock_production_faostat?fields=country,year,species,population&query=year=2017%20AND%20species=%27Goats%27&format=html

#### API Parameters
**Required Parameters**
1. table_name - this is the name of the table you want to query.
    1. You can get a list of the tables by using the GBADsTable API
2. fields - this is the list of columns you want to return.
    1. Use by setting fields = column name. If you don't know the column names you can use '*' instead to return all columns.
3. query - this is the query you want to run on the table (ex. Query: year=2017 AND species='Goats').
    1. The query is in the same format as a standard SQL query. Done by setting query tag equal to the query you want. Use '%20' as placeholders for spaces. An example of a query is as follows:
http://gbadske.org:9000/GBADsPublicQuery/livestock_production_faostat?fields=country,year,species,population&query=year=2017%20AND%20species=%27Goats%27AND%20species=%27asses%27&format=html. Notice in the query how around 'AND' statements there is a %20 and around strings for query terms there's %27. When string value in a query is besides an AND or OR statement, the %27 from the string takes presedence over the %20 from the AND or OR.

**Optional Parameters**

4. join - this is the join you want to run on another table. This is used to join the table you are querying with another table.
    - It will default to no join if no join is specified
5. order - this is the order you want to return the results in.
    - It will default to no order if no order is specified
6. format - this is the format you want the results returned in (html or text/csv).
    - It will default to csv if no format is specified
    - You can set it to *html* to return html, otherwise it will return a csv file
7. count - If set to anything other than no, returns the number of rows returned by the query.
    - It will default to no if no count is specified

#### Output Example
```
GBADs Public Database Query

SELECT country,year,species,population FROM livestock_production_faostat WHERE year=2017 AND species='Goats'

| country	            | year	      | species	  | population |
| --------------------- | ----------- | --------- | ---------- |
| Afghanistan           | 2017        | Goats     |	7598000    |
| Albania	            | 2017	      | Goats	  | 933121     |
| Algeria	            | 2017	      | Goats	  | 5007894    |
| Angola	            | 2017	      | Goats	  | 4530221    |
| Antigua and Barbuda	| 2017	      | Goats	  | 27000      |
```

## GBADsLivestockPopulation
#### Endpoint Introduction

This API returns the population of livestock in a country for a given year.

#### How to run
You can access this API by going to either
1. http://gbadske.org:9000/GBADsLivestockPopulation/faostat?year=2017&country=Canada&species=*&format=file

or if you're running it locally

2. http://localhost:9000/GBADsLivestockPopulation/oie?year=*&country=Canada&species=Cattle&format=html

#### API Parameters
**Required Parameters**
The elements of the API that can be configured are:
1. data source: This is either *oie* or *faostat* (As seen in the examples above).
2. format: This can be either set to *html* or *file*. File returns a CSV file of the results.

**Optional Parameters**

3. year: For which year you would like to see the animal populations of. If set to * then it will return all years.
    - This defaults to all years if not set
4. country: For which country you would like to see the animal populations of. If set to * then it will return all countries.
    - This defaults to all countries if not set
5. species: For which species you would like to see the animal populations of. If set to * then it will return all species.
    - This defaults to all species if not set
    - Since there are different subclasses of the same species (ex. Adult Beef Cattle and Adult Dairy Cattle), you can set the species tag to the following to get all of a specific type of animal for the **oie data source only**:
        - 'Poultry' will return all poultry such as Birds, (egg) Layers, Broilers, Turkeys and other commercial poultry
        - 'All Cattle' will return all tupes of Cows such as Male and females cattle, adult beef cattle, adult dairy cattle, etc.
        - 'All Swine' will return all types of swine such as Commerical pigs, fattening pigs, etc.
        - 'All Sheep' will return all types of sheep such as Adult sheep, lambs, etc.
        - 'All Equids' will return all tupes of horses
    - If you're using **faostat** you can use:
        - 'Poultry' will return all poultry such as Chickens, Turkeys, Ducks, Geese, and Guineas
6. iso3: You can only choose this if your data source is faostat. This is the ISO3 code for the country you want to query. If set to * then it will return all countries.
    - This defaults to all IOS' if not set

#### Output Example
```
GBADs Public Database Query: livestock_national_population_oie

SELECT country,year,species,population,metadataflags FROM livestock_national_population_oie WHERE country='Canada' AND species='Cattle'

| country	| year	| species	| population  |metadataflags |
| --------- | ----- | --------- | ----------- | ------------ |
| Canada	| 2005	| Cattle	| 14830000	  | RAW0001      |
| Canada	| 2006	| Cattle	| 14315000	  | RAW0001      |
| Canada	| 2007	| Cattle	| 13945000	  | RAW0001      |
| Canada	| 2008	| Cattle	| 13180000	  | RAW0001      |
| Canada	| 2009	| Cattle	| 13015000	  | RAW0001      |
```
