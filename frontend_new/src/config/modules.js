import { Search, Scale, FileText, Settings, Zap, Bell, Brain } from 'lucide-react'

const modules = [
  { id: 'research', label: 'Research', icon: Brain, description: 'Multi-agent legislative research' },
  { id: 'explore', icon: FileText, label: 'Explore', description: 'Browse & search all bills' },
  { id: 'amendments', icon: Scale, label: 'Amendments', description: 'Delta-aware legislative diff' },
  { id: 'alerts', icon: Bell, label: 'Alerts', description: 'Email alerts for bills & topics' },
  { id: 'architecture', icon: Settings, label: 'Architecture', description: 'Live system inventory' },
  { id: 'playground', icon: Zap, label: 'Playground', description: 'Model comparison & testing' },
  { id: 'search', icon: Search, label: 'Search', description: 'Semantic & keyword search' },
]

export default modules