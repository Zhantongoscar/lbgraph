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