#include "core/StructureAggregateCensus.h"

#include <array>
#include <iostream>
#include <stdexcept>
#include <vector>

namespace
{
    using Obelisk::Core::StructureAggregateCensus;
    using Obelisk::Core::StructureAggregateCensusOptions;
    using Obelisk::Core::StructureEventKind;
    using Obelisk::Core::StructureEventView;
    using Obelisk::Core::StructureScalarField;
    using Obelisk::Core::StructureScalarType;
    using Obelisk::Core::StructureScalarValue;

    void Require(bool condition, const char* message)
    {
        if (!condition)
            throw std::runtime_error(message);
    }

    StructureScalarValue BoolScalar(StructureScalarField field, bool value)
    {
        return {
            .Field = field,
            .Type = StructureScalarType::Bool,
            .BoolValue = value,
            .Int32Value = 0,
        };
    }

    StructureScalarValue Int32Scalar(StructureScalarField field, int32_t value)
    {
        return {
            .Field = field,
            .Type = StructureScalarType::Int32,
            .BoolValue = false,
            .Int32Value = value,
        };
    }

    StructureEventView Event(StructureEventKind kind, const std::vector<StructureScalarValue>& scalars)
    {
        return {
            .Kind = kind,
            .FunctionNameIndex = 1234,
            .OuterNameIndex = 5678,
            .Scalars = scalars,
        };
    }

    void TestDefaultOffClearsAndRejects()
    {
        StructureAggregateCensus census;
        const std::vector<StructureScalarValue> scalars = {
            BoolScalar(StructureScalarField::ReturnValue, true),
        };

        Require(!census.Accumulate(Event(StructureEventKind::AllowStructureAccess, scalars), true),
                "default-off structure census accepted an event");
        const auto snapshot = census.Snapshot();
        Require(snapshot.MatchedTotal == 0, "default-off structure census kept matches");
        Require(snapshot.WindowEventsSeen == 0, "default-off structure census consumed window budget");
    }

    void TestBoundedCountersAndCappedVariantHistogram()
    {
        StructureAggregateCensus census({
            .Enabled = true,
            .WindowEventLimit = 9,
            .VariantBucketLimit = 2,
        });

        const std::vector<StructureScalarValue> returnTrue = {
            BoolScalar(StructureScalarField::ReturnValue, true),
        };
        const std::vector<StructureScalarValue> returnFalse = {
            BoolScalar(StructureScalarField::ReturnValue, false),
        };
        const std::vector<StructureScalarValue> variant3 = {
            Int32Scalar(StructureScalarField::VariantIndex, 3),
            BoolScalar(StructureScalarField::BForceSet, true),
            BoolScalar(StructureScalarField::ReturnValue, false),
        };
        const std::vector<StructureScalarValue> variant4 = {
            Int32Scalar(StructureScalarField::VariantIndex, 4),
            BoolScalar(StructureScalarField::BForceSet, false),
            BoolScalar(StructureScalarField::ReturnValue, true),
        };
        const std::vector<StructureScalarValue> variant99 = {
            Int32Scalar(StructureScalarField::VariantIndex, 99),
            BoolScalar(StructureScalarField::BForceSet, true),
            BoolScalar(StructureScalarField::ReturnValue, true),
        };
        const std::vector<StructureScalarValue> canSeat = {
            BoolScalar(StructureScalarField::BForce, true),
            BoolScalar(StructureScalarField::ReturnValue, true),
        };

        Require(census.Accumulate(Event(StructureEventKind::AllowStructureAccess, returnTrue), true),
                "access structure event was rejected");
        Require(census.Accumulate(Event(StructureEventKind::IsAllowedToDemolish, returnFalse), true),
                "demolish structure event was rejected");
        Require(census.Accumulate(Event(StructureEventKind::AllowToggleActivation, returnTrue), true),
                "toggle structure event was rejected");
        Require(census.Accumulate(Event(StructureEventKind::SetVariant, variant3), true),
                "variant 3 structure event was rejected");
        Require(census.Accumulate(Event(StructureEventKind::SetVariant, variant4), true),
                "variant 4 structure event was rejected");
        Require(census.Accumulate(Event(StructureEventKind::SetVariant, variant99), true),
                "variant 99 structure event was rejected");
        Require(!census.Accumulate(Event(StructureEventKind::VerifyPinCode, returnTrue), true),
                "PIN check structure event was accepted into aggregate census");
        Require(census.Accumulate(Event(StructureEventKind::CanSeat, canSeat), true),
                "seat structure event was rejected");
        Require(census.Accumulate(Event(StructureEventKind::SetVariant, variant4), false),
                "post-original-blocked variant structure event was rejected");

        const auto snapshot = census.Snapshot();
        Require(snapshot.WindowEventsSeen == 9, "structure census window count mismatch");
        Require(snapshot.MatchedTotal == 8, "structure census match count mismatch");
        Require(snapshot.OriginalCalledTotal == 7, "structure census original-called count mismatch");
        Require(snapshot.OriginalBlockedTotal == 1, "structure census original-blocked count mismatch");
        Require(snapshot.RejectedSensitiveOrNonStructure == 1,
                "structure census did not reject PIN/non-structure event");
        Require(snapshot.RejectedUnexpectedField == 0, "structure census rejected valid field shape");

        const auto returnValue = snapshot.FieldCounters[static_cast<size_t>(StructureScalarField::ReturnValue)];
        Require(returnValue.Present == 7, "return value present count mismatch");
        Require(returnValue.BoolTrue == 5, "return value true count mismatch");
        Require(returnValue.BoolFalse == 2, "return value false count mismatch");

        const auto forceSet = snapshot.FieldCounters[static_cast<size_t>(StructureScalarField::BForceSet)];
        Require(forceSet.Present == 3, "force-set present count mismatch");
        Require(forceSet.BoolTrue == 2, "force-set true count mismatch");
        Require(forceSet.BoolFalse == 1, "force-set false count mismatch");

        const auto variant = snapshot.FieldCounters[static_cast<size_t>(StructureScalarField::VariantIndex)];
        Require(variant.Present == 3, "variant index present count mismatch");
        Require(variant.Int32Present == 3, "variant index int32 count mismatch");
        Require(snapshot.VariantIndexBuckets[0].Used && snapshot.VariantIndexBuckets[0].Value == 3 &&
                    snapshot.VariantIndexBuckets[0].Count == 1,
                "first variant histogram bucket mismatch");
        Require(snapshot.VariantIndexBuckets[1].Used && snapshot.VariantIndexBuckets[1].Value == 4 &&
                    snapshot.VariantIndexBuckets[1].Count == 1,
                "second variant histogram bucket mismatch");
        Require(!snapshot.VariantIndexBuckets[2].Used, "variant histogram exceeded configured bucket cap");
        Require(snapshot.VariantIndexOther == 1, "variant histogram other count mismatch");
    }

    void TestRejectsUnexpectedShapeAndWindowOverflow()
    {
        StructureAggregateCensus census({
            .Enabled = true,
            .WindowEventLimit = 2,
            .VariantBucketLimit = 2,
        });

        const std::vector<StructureScalarValue> wrongShape = {
            BoolScalar(StructureScalarField::BForceSet, true),
        };
        const std::vector<StructureScalarValue> returnTrue = {
            BoolScalar(StructureScalarField::ReturnValue, true),
        };

        Require(!census.Accumulate(Event(StructureEventKind::AllowStructureAccess, wrongShape), true),
                "structure census accepted unexpected copied field shape");
        Require(census.Accumulate(Event(StructureEventKind::AllowStructureAccess, returnTrue), true),
                "structure census rejected valid event after invalid shape");
        Require(!census.Accumulate(Event(StructureEventKind::AllowStructureAccess, returnTrue), true),
                "structure census accepted event past window limit");

        const auto snapshot = census.Snapshot();
        Require(snapshot.WindowEventsSeen == 2, "structure census window consumed past limit");
        Require(snapshot.MatchedTotal == 1, "structure census matched invalid shape");
        Require(snapshot.RejectedUnexpectedField == 1, "structure census did not count invalid shape rejection");
        Require(snapshot.RejectedWindowFull == 1, "structure census did not count window overflow");
    }
}

int main()
{
    try
    {
        TestDefaultOffClearsAndRejects();
        TestBoundedCountersAndCappedVariantHistogram();
        TestRejectsUnexpectedShapeAndWindowOverflow();
    }
    catch (const std::exception& e)
    {
        std::cerr << "StructureAggregateCensusTests failed: " << e.what() << "\n";
        return 1;
    }

    std::cout << "StructureAggregateCensusTests passed\n";
    return 0;
}
