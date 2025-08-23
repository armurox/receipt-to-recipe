import React, { useEffect, useState } from 'react'

const API_BASE = import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8081/api'

export default function App(){
  const [ingredients, setIngredients] = useState([])
  const [selected, setSelected] = useState(new Set())
  const [recipes, setRecipes] = useState([])
  const [file, setFile] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [availableModels, setAvailableModels] = useState([])
  const [selectedModel, setSelectedModel] = useState('')

  const loadIngredients = async () => {
    try{
      const res = await fetch(`${API_BASE}/ingredients/`)
      setIngredients(await res.json())
    }catch(e){ setError('Failed to load ingredients') }
  }

  const loadSettings = async () => {
    try{
      const res = await fetch(`${API_BASE}/settings/`)
      const data = await res.json()
      setAvailableModels(data.available_models)
      setSelectedModel(data.current_model)
    }catch(e){ setError('Failed to load settings') }
  }

  useEffect(()=>{ 
    loadIngredients()
    loadSettings()
  }, [])

  const toggle = (id) => {
    const s = new Set(selected)
    if (s.has(id)) s.delete(id); else s.add(id)
    setSelected(s)
  }

  const upload = async (e) => {
    e.preventDefault()
    if(!file) return
    setLoading(true); setError('')
    const form = new FormData()
    form.append('image', file)
    if(selectedModel) form.append('model', selectedModel)
    try{
      const res = await fetch(`${API_BASE}/receipts/`, { method: 'POST', body: form })
      if(!res.ok) throw new Error('upload failed')
      await res.json()
      await loadIngredients()
      setFile(null)
    }catch(e){ setError('Upload/OCR failed - you can retry with the same file') }
    finally{ setLoading(false) }
  }

  const getRecipes = async () => {
    if(selected.size===0){ setError('Pick at least one ingredient'); return }
    setLoading(true); setError('')
    try{
      const res = await fetch(`${API_BASE}/recipes/`, {
        method: 'POST', 
        headers: { 'Content-Type':'application/json' },
        body: JSON.stringify({ ingredient_ids: Array.from(selected), number: 12 })
      })
      if(!res.ok) throw new Error('fetch failed')
      setRecipes(await res.json())
    }catch(e){ setError('Recipe fetch failed') }
    finally{ setLoading(false) }
  }

  const clearError = () => setError('')

  return (
    <div className="wrap">
      <h1>Receipt → Recipe</h1>
      
      <div className="card">
        <h3>OCR Model Settings</h3>
        <div style={{marginBottom: 12}}>
          <label>Choose OCR Model:</label>
          <select value={selectedModel} onChange={(e) => setSelectedModel(e.target.value)} style={{marginLeft: 8, padding: 4}}>
            {availableModels.map(model => (
              <option key={model.id} value={model.id}>{model.name}</option>
            ))}
          </select>
        </div>
      </div>

      <div className="card">
        <h3>Upload a receipt</h3>
        <form onSubmit={upload}>
          <input type="file" accept="image/*" onChange={(e)=>{setFile(e.target.files?.[0] || null); clearError()}} />
          <div style={{marginTop: 8}}>
            <button disabled={loading || !file} type="submit">
              {loading ? 'Processing...' : 'Upload & Extract'}
            </button>
            {file && error && (
              <button type="button" onClick={() => setFile(null)} style={{marginLeft: 8, background: '#ccc'}}>
                Clear File
              </button>
            )}
          </div>
        </form>
        {error && (
          <div style={{color:'#b00', marginTop: 8}}>
            {error}
            {file && (
              <div style={{marginTop: 4}}>
                <button onClick={clearError} style={{fontSize: '12px', padding: '2px 8px'}}>
                  Dismiss
                </button>
              </div>
            )}
          </div>
        )}
        {file && (
          <p style={{color:'#666', fontSize:'14px', marginTop: 8}}>
            File ready: {file.name}
          </p>
        )}
      </div>

      <div className="card">
        <h3>Select ingredients</h3>
        <div className="grid cols-2">
          {ingredients.map(i => (
            <label key={i.id} className="badge">
              <input type="checkbox" checked={selected.has(i.id)} onChange={()=>toggle(i.id)} /> {i.name}
            </label>
          ))}
        </div>
        <button disabled={loading} style={{marginTop:12}} onClick={getRecipes}>Find recipes</button>
      </div>

      <div className="card">
        <h3>Recipes</h3>
        <div className="recipes">
          {recipes.map(r => (
            <div key={r.id} className="card">
              <img src={r.image} alt={r.title} />
              <h4>{r.title}</h4>
              <div>
                <span className="badge">Used: {r.usedIngredientCount}</span>
                <span className="badge">Missing: {r.missedIngredientCount}</span>
              </div>
              <p><a href={`https://spoonacular.com/recipes/${encodeURIComponent(r.title)}-${r.id}`} target="_blank" rel="noreferrer">Open on Spoonacular →</a></p>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
