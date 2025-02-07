# import csv
# from neo4j import GraphDatabase

# class DataImporter:
#     def __init__(self, uri, user, password):
#         self.driver = GraphDatabase.driver(uri, auth=(user, password))

#     def close(self):
#         self.driver.close()

#     def import_data(self):
#         uri = "bolt://192.168.35.10:7687"
#         user = "neo4j"
#         password = "13701033228"
        
#         with self.driver.session() as session:
#             with open('data/SmartWiringzta.csv', mode='r', encoding='utf-8') as file:
#                 csv_reader = csv.DictReader(file)
#                 for row in csv_reader:
#                     source = row['source']
#                     target = row['target']
#                     wire_type = row['Consecutive number']
#                     length = row['Length (full)']
#                     color = row['Connection color / number']
#                     cross_section = row['Connection: Cross-section / diameter']
#                     connection_type = row['Connection: Type designation']
#                     source_processing = row['Wire termination processing source']
#                     target_processing = row['Wire termination processing target']
#                     source_routing = row['Routing direction source']
#                     target_routing = row['Routing direction target']
#                     bundle = row['Bundle']
#                     layout_space = row['Layout space: Routing track']
#                     connection_designation = row['Connection designation']
#                     remark = row['Remark']
                    
#                     # Create source node
#                     session.run("""
#                     MERGE (s:Vertex {name: $source})
#                     ON CREATE SET s.Location = 'K1.' + $location, s.Terminal = $terminal, s.Function = $function, s.UnitType = $unit_type, s.DeviceId = $device_id, s.Device = $device, s.Voltage = $voltage, s.IsEnabled = $is_enabled
#                     """, source=source, location=source.split('+')[1].split(':')[0], terminal=source.split('+')[1].split(':')[1], function='B', unit_type='B', device_id=1, device='1', voltage=0.0, is_enabled=True)
                    
#                     # Create target node
#                     session.run("""
#                     MERGE (t:Vertex {name: $target})
#                     ON CREATE SET t.Location = 'K1.' + $location, t.Terminal = $terminal, t.Function = $function, t.UnitType = $unit_type, t.DeviceId = $device_id, t.Device = $device, t.Voltage = $voltage, t.IsEnabled = $is_enabled
#                     """, target=target, location=target.split('+')[1].split(':')[0], terminal=target.split('+')[1].split(':')[1], function='B', unit_type='B', device_id=1, device='1', voltage=0.0, is_enabled=True)
                    
#                     # Create relationship
#                     session.run("""
#                     MATCH (s:Vertex {name: $source}), (t:Vertex {name: $target})
#                     MERGE (s)-[r:CONNECTS {type: $connection_type, wireType: $wire_type, length: $length, color: $color, crossSection: $cross_section, sourceProcessing: $source_processing, targetProcessing: $target_processing, sourceRouting: $source_routing, targetRouting: $target_routing, bundle: $bundle, layoutSpace: $layout_space, connectionDesignation: $connection_designation, remark: $remark}]->(t)
#                     """, source=source, target=target, connection_type=connection_type, wire_type=wire_type, length=length, color=color, cross_section=cross_section, source_processing=source_processing, target_processing=target_processing, source_routing=source_routing, target_routing=target_routing, bundle=bundle, layout_space=layout_space, connection_designation=connection_designation, remark=remark)

# if __name__ == "__main__":
#     importer = DataImporter("bolt://192.168.35.10:7687", "neo4j", "13701033228")
#     importer.import_data()
#     importer.close()

import csv

class DataImporter:
    def __init__(self, uri, user, password):
        pass
    def close(self):
        pass
    def import_data(self):
        with open('data/SmartWiringzta.csv', mode='r', encoding='utf-8') as file:
            csv_reader = csv.DictReader(file)
            for row in csv_reader:
                source = row['source']
                target = row['target']
                
                # Skip if source or target doesn't contain '+' and ':'
                if '+' not in source or ':' not in source or '+' not in target or ':' not in target:
                    print(f"Skipping row with invalid source or target: source={source}, target={target}")
                    continue
                
                wire_type = row['Consecutive number']
                length = row['Length (full)']
                color = row['Connection color / number']
                cross_section = row['Connection: Cross-section / diameter']
                connection_type = row['Connection: Type designation']
                source_processing = row['Wire termination processing source']
                target_processing = row['Wire termination processing target']
                source_routing = row['Routing direction source']
                target_routing = row['Routing direction target']
                bundle = row['Bundle']
                layout_space = row['Layout space: Routing track']
                connection_designation = row['Connection designation']
                remark = row['Remark']

                # Placeholder for actual server communication logic
                print(f"Processing: source={source}, target={target}, wire_type={wire_type}, length={length}, color={color}")

if __name__ == "__main__":
    importer = DataImporter("bolt://192.168.35.10:7687", "neo4j", "13701033228")
    importer.import_data()
    importer.close()