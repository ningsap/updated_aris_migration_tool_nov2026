import pickle

  with open('input/<your_scb_input_file>.pickle', 'rb') as f:
      data = pickle.load(f)

  models = data.get('models', {})

  # Find a BPMN model that has "Baseline Data" in the name
  for mid, m in models.items():
      if 'Baseline' in m.get('name', '') and 'bpmn' in m.get('type', '').lower():
          print(f"Model: {m.get('name')} | scale={m.get('scale')} | guid={mid}")
          occs = m.get('occs', {})
          for occ_id, occ in occs.items():
              sym = occ.get('symbol', '')
              pos = occ.get('position', {})
              size = occ.get('size', {})
              print(f"  {occ_id} | sym={sym} | pos={pos} | size={size}")
          break
