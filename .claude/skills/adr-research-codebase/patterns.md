# Codebase Patterns

> Populated by `/init` — update as patterns are discovered

## File Organization

<!-- Example patterns - customize after /init -->

```
src/
├── components/     # React components
│   ├── ui/        # Primitive UI components
│   └── features/  # Feature-specific components
├── hooks/         # Custom React hooks
├── stores/        # State management
├── api/           # API layer
├── utils/         # Helper functions
└── types/         # TypeScript types
```

## Naming Conventions

| Type | Pattern | Example |
|------|---------|---------|
| Components | PascalCase | `UserProfile.tsx` |
| Hooks | camelCase, use* prefix | `useAuth.ts` |
| Stores | camelCase, *Store suffix | `userStore.ts` |
| Utils | camelCase | `formatDate.ts` |
| Types | PascalCase | `User.ts` |

## Component Pattern

```typescript
// Standard component structure
interface Props {
  // Props definition
}

export function ComponentName({ prop }: Props) {
  // Hooks first
  const [state, setState] = useState();
  
  // Derived state
  const computed = useMemo(() => {}, []);
  
  // Effects
  useEffect(() => {}, []);
  
  // Handlers
  const handleAction = () => {};
  
  // Render
  return <div />;
}
```

## State Management Pattern

<!-- Customize based on actual state library -->

```typescript
// Zustand store pattern
import { create } from 'zustand';

interface Store {
  data: Data[];
  loading: boolean;
  fetch: () => Promise<void>;
}

export const useStore = create<Store>((set) => ({
  data: [],
  loading: false,
  fetch: async () => {
    set({ loading: true });
    const data = await api.getData();
    set({ data, loading: false });
  },
}));
```

## API Pattern

<!-- Customize based on actual API approach -->

```typescript
// API call pattern
export async function fetchData(params: Params): Promise<Data> {
  const response = await fetch(`/api/endpoint`, {
    method: 'POST',
    body: JSON.stringify(params),
  });
  
  if (!response.ok) {
    throw new Error('Failed to fetch');
  }
  
  return response.json();
}
```

## Testing Pattern

<!-- Customize based on test framework -->

```typescript
// Test pattern
describe('ComponentName', () => {
  it('should render correctly', () => {
    render(<ComponentName />);
    expect(screen.getByRole('button')).toBeInTheDocument();
  });
  
  it('should handle user interaction', async () => {
    render(<ComponentName />);
    await userEvent.click(screen.getByRole('button'));
    expect(mockFn).toHaveBeenCalled();
  });
});
```

## Discovered Patterns

<!-- Add patterns discovered during development -->

| Pattern | Location | Usage |
|---------|----------|-------|
| *Run /init to populate* | | |
