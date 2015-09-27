-- testing lua stuff
-- by dan

if (3 == 4) then
  print("equal")
else
  print("not equal")
end

for x=0,20,3 do
  print(x)
end
print("")
x = 1
while(x <= 5) do
  print(x)
  x = x + 1
end
print("")

y = 0
function plusone(x)
  local y = x + 1
  return y
end
print(plusone(2))
print(y)

a = {1,2,3,4}
a[3] = a[4]
foreach(a, print)
print("count a: ", count(a))
print("")

b = {}
b.x = 2
b.y = 2
foreach(b, print)
print("count b: ", count(b))

print("a", "b", "c")
print("")

print("start")
for z=0,40 do
  print(z)
end
print("end")

a = {"hello", "blah"}
add(a, "world")
del(a, "blah")
print(count(a))
foreach(a, print)
foreach(a, function(i) print(i) end)
