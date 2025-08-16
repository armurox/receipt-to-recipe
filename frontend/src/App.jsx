import React, { useEffect, useState } from 'react'

const API_BASE = import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8000/api'

export default function App(){
  const [ingredients, setIngredients] = useState([])
  const [selected, setSelected] = useState(new Set())
  const [recipes, setRecipes] = useState([])
  const [file, setFile] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const loadIngredients = async () => {
    try{
      const res = await fetch(`${API_BASE}/ingredients/`)
      const data = await res.json()
      setIngredients(data)
    }catch(e){ setError('Failed to load ingredients') }
  }

  useEffect(()=>{ loadIngredients() }, [])

  const toggle = (id) => {
    const s = new Set(selected)
    if (s.has(id)) s.delete(id); else s.add(id)
    setSelected(s)
  }

  const upload = async (e) => {
    e.preventDefault()
    if(!file){ return }
    setLoading(true); setError('')
    const form = new FormData()
    form.append('image', file)
    try{
      const res = await fetch(`${API_BASE}/receipts/`, { method: 'POST', body: form })
      if(!res.ok){ throw new Error('upload failed') }
      await res.json()
      await loadIngredients()
    }catch(e){ setError('Upload/OCR failed') }
    finally{ setLoading(false); setFile(null) }
  }

  const getRecipes = async () => {
    if(selected.size===0){ setError('Pick at least one ingredient'); return }
    setLoading(true); setError('')
    try{
      const res = await fetch(`${API_BASE}/recipes/`, {
        method: 'POST', headers: { 'Content-Type':'application/json' },
        body: JSON.stringify({ ingredient_ids: Array.from(selected), number: 12 })
      })
      if(!res.ok){ throw new Error('fetch failed') }
      const data = await res.json()
      setRecipes(data)
    }catch(e){ setError('Recipe fetch failed') }
    finally{ setLoading(false) }
  }

  return (
    <div className="wrap">
      <h1>Receipt → Recipe</h1>
      <div className="card">
        <h3>Upload a receipt</h3>
        <form onSubmit={upload}>
          <input type="file" accept="image/*" onChange={(e)=>setFile(e.target.files?.[0] || null)} />
          <button disabled={loading || !file} type="submit">Upload & Extract</button>
        </form>
        <p style={{color:'#b00'}}>{error}</p>
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
