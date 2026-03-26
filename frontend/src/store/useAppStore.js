import { create } from "zustand";

const useAppStore = create((set) => ({
  user: null,
  setUser: (user) => set({ user }),
  predictions: [],
  addPrediction: (p) => set((state) => ({ predictions: [...state.predictions, p] })),
}));

export default useAppStore;
