package main

/*
#include <stdint.h>
*/
import "C"
import (
    "math"
    "math/rand"
)

// CinnamonDamage is a deterministic, CPU-only combat formula used by the
// Python RPG layer when this optional native library is built.
//export CinnamonDamage
func CinnamonDamage(atk, defense, crit, luck C.double, seed C.uint64_t) C.int {
    r := rand.New(rand.NewSource(int64(seed)))
    raw := float64(atk) + float64(r.Intn(9)-2) - float64(defense)*0.45
    if raw < 1 { raw = 1 }
    if r.Float64() < float64(crit)+float64(luck)*0.25 { raw *= 1.75 }
    return C.int(math.Round(raw))
}

func main() {}
