
class EPlusTmpl:
    elec_tmpl =    "SELECT C.'Month', C.'Day', C.'Hour', C.'Minute', C.'Dst', A.'Value'/{unit_conversion} AS 'value' " \
                   "FROM 'ReportData' A " \
                       "INNER JOIN 'ReportDataDictionary' B " \
                           "ON A.'ReportDataDictionaryIndex' = B.'ReportDataDictionaryIndex' " \
                       "INNER JOIN 'Time' C ON A.'TimeIndex' = C.'TimeIndex' " \
                   "WHERE B.'Name'='{point_name}' " \
                       "AND C.'EnvironmentPeriodIndex' = 3 " \
                   "ORDER BY C.'Month', C.'Day', C.'Hour', C.'Minute'"

    gas_tmpl =    "SELECT C.'Month', C.'Day', C.'Hour', C.'Minute', C.'Dst', A.'Value'/3600000 AS 'value' " \
               "FROM 'ReportData' A " \
                   "INNER JOIN 'ReportDataDictionary' B " \
                       "ON A.'ReportDataDictionaryIndex' = B.'ReportDataDictionaryIndex' " \
                   "INNER JOIN 'Time' C ON A.'TimeIndex' = C.'TimeIndex' " \
               "WHERE B.'Name'='Gas:Facility' " \
                   "AND C.'EnvironmentPeriodIndex' = 3 " \
               "ORDER BY C.'Month', C.'Day', C.'Hour', C.'Minute'"

    zones_tmpl = "SELECT ZoneName FROM Zones"

    zone_tmpl =    "SELECT C.'Month', C.'Day', C.'Hour', C.'Minute', C.'Dst', A.'Value'*1.8+32 AS '{alias}' " \
                   "FROM 'ReportData' A " \
                      "INNER JOIN 'ReportDataDictionary' B " \
                      "ON A.'ReportDataDictionaryIndex' = B.'ReportDataDictionaryIndex' " \
                      "INNER JOIN 'Time' C ON A.'TimeIndex' = C.'TimeIndex' " \
                   "WHERE B.'Name' = '{name}' " \
                      "AND B.'KeyValue' = '{key}' " \
                      "AND C.'EnvironmentPeriodIndex' = 3 " \
                   "ORDER BY C.'Month', C.'Day', C.'Hour', C.'Minute'"

    zone_temp_name = "Zone Mean Air Temperature"

    # Building1 and Large office
    cooling_ext1 = "Zone Thermostat Cooling Setpoint Temperature"
    heating_ext1 = "Zone Thermostat Heating Setpoint Temperature"

    # Small and medium office
    cooling_ext2 = '_COOL 1/0'
    heating_ext2 = '_HEAT 1/0'

    @classmethod
    def get_zone_temp_query(cls, bldg, zone_name, alias='value'):
        return cls.zone_tmpl.replace('{key}', zone_name)\
            .replace('{name}', cls.zone_temp_name)\
            .replace('{alias}', alias)

    @classmethod
    def get_zone_cooling_sp_query(cls, bldg, zone_name, alias='value'):
        name, key = cls.get_cooling_sp(bldg, zone_name)
        return cls.zone_tmpl.replace('{key}', key) \
            .replace('{name}', name)\
            .replace('{alias}', alias)

    @classmethod
    def get_zone_heating_sp_query(cls, bldg, zone_name, alias='value'):
        name, key = cls.get_heating_sp(bldg, zone_name)
        return cls.zone_tmpl.replace('{key}', key) \
            .replace('{name}', name) \
            .replace('{alias}', alias)

    @classmethod
    def get_cooling_sp(cls, bldg, zone_name):
        name = cls.cooling_ext1
        key = zone_name
        if 'small_office' in bldg or 'medium_office' in bldg:
            name = 'Schedule Value'
            key = zone_name + cls.cooling_ext2

        return name, key

    @classmethod
    def get_heating_sp(cls, bldg, zone_name):
        name = cls.heating_ext1
        key = zone_name
        if 'small_office' in bldg or 'medium_office' in bldg:
            name = 'Schedule Value'
            key = zone_name + cls.heating_ext2

        return name, key

    @classmethod
    def get_power_point(cls, bldg):
        point = 'Electricity:Facility'
        unit_conversion = str(3600000)
        if 'building1' in bldg:
            point = 'Facility Total Electric Demand Power'
            unit_conversion = str(1000)

        return cls.elec_tmpl.replace('{point_name}', point).replace('{unit_conversion}', unit_conversion)
